from httpx import HTTPError, TimeoutException
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
import logging
from pydantic import BaseModel, Field
from typing import Annotated
import uuid

logger = logging.getLogger(__name__)

class LongTermMemoryMerge(BaseModel):
    updated_memory: str = Field(
        description = "Texto consolidado de la memoria manteniendo lo antiguo y añadiendo/corrigiendo lo nuevo."
    )

def store_or_update_long_term_memory(new_info: str, memory_namespace, ollama_url: str, store: Annotated[BaseStore, InjectedStore()]):
    logger.debug("Processing new info: %s. Namespace: %s", new_info, memory_namespace)

    current_memory_results = store.search(memory_namespace, query=new_info, limit=1)
    
    if current_memory_results and current_memory_results[0].score is not None and current_memory_results[0].score >= 0.75:
        logger.debug("Found something related")

        # There is something similar in the long term memory, we'll update it
        found_key = current_memory_results[0].key
        previous_info = current_memory_results[0].value["texto"]
    
        logger.info("Contacting Ollama in %s", ollama_url)
        llm_ollama = ChatOllama(
            base_url = ollama_url,
            model = "qwen2.5:1.5b",
            temperature = 0.0 # We just want data to be merged, nothing new to be added
        )

        structured_llm = llm_ollama.with_structured_output(LongTermMemoryMerge)

        system_prompt = """
        Eres un módulo de gestión de memoria a largo plazo.
        Analiza la MEMORIA EXISTENTE y la NUEVA INFORMACIÓN para generar la MEMORIA ACTUALIZADA.

        REGLAS:
        1. Mantiene la información antigua salvo que la nueva la contradiga explícitamente.
        2. Si la nueva información contradice a la antigua, actualízala.
        3. Si la nueva información es irrelevante o duplicada, no hagas cambios.
        4. Redacta en tercera persona de forma clara y concisa."""

        memory_update_prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "MEMORIA EXISTENTE:\n{current_memory}\n\nNUEVA INFORMACIÓN:\n{new_info}")
        ])

        merge_chain = memory_update_prompt_template | structured_llm.with_retry()

        try:
            res = merge_chain.invoke({
                "current_memory": previous_info,
                "new_info": new_info
            })
            updated_text = res.updated_memory
        except (HTTPError, TimeoutException) as e:
            logger.error("Ollama service unavailable at %s: %s. Applying fallback.", ollama_url, e)
            updated_text = f"{previous_info} [Info adicional]: {new_info}"

        logger.debug("Updated memory: %s", updated_text)
        
        store.put(
            namespace = memory_namespace,
            key = found_key,
            value = {"texto": updated_text}
        )
    else:
        logger.debug("Looks new")
        # There is nothing related in the long term memory
        store.put(
            namespace = memory_namespace,
            key = str(uuid.uuid4()),
            value={"texto": new_info}
        )
