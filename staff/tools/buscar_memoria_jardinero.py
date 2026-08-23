from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from typing import Annotated

from longTermMemory import search_long_term_memory

@tool
def buscar_memoria_jardinero(texto_a_buscar: str, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    """Busca en la memoria a largo plazo del jardinero."""

    user_id = config.get("configurable", {}).get("user_id")
    memory_namespace = (user_id, "gardener")
    return search_long_term_memory(texto_a_buscar, memory_namespace, store=store, emptyMsg="No se encontró ninguna información relevante en la memoria.")
