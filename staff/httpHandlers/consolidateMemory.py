from fastapi import APIRouter, Depends, Request
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langchain_core.messages import RemoveMessage

from longTermMemory import store_or_update_long_term_memory
from state import retrieve_older_than_24h
from .common import get_graph, get_store

router = APIRouter()


def get_engine(request: Request):
    return request.app.state.engine

@router.post("/consolidate-memory")
async def consolidate_memory(request: Request, graph: CompiledStateGraph = Depends(get_graph), store: BaseStore = Depends(get_store), engine = Depends(get_engine)):

    # Retrieve state
    config = {"configurable": {"thread_id": "1", "user_id": 1}}
    state = await graph.aget_state(config)

    # Prompt for the memory consolidator
    system_prompt = """
    Eres un sistema encargado de consolidar la memoria a largo plazo de un hogar.

    Analiza:
    1. La conversación mantenida durante las últimas 24 horas.
    2. La memoria a largo plazo que ya existe.

    Tu objetivo es identificar información nueva de la conversación que merezca conservarse como memoria a largo plazo.

    Una memoria debe representar información que pueda ser útil en interacciones futuras, como:
    - preferencias del usuario
    - hábitos y rutinas
    - instrucciones persistentes
    - información relevante sobre el hogar
    - información relevante sobre personas y elementos del hogar
    - cambios permanentes o duraderos en las preferencias o rutinas

    No incluyas:
    - conversaciones triviales
    - saludos o despedidas
    - información que solo sea relevante para la conversación actual
    - información temporal que probablemente deje de ser relevante
    - información que ya esté recogida en la memoria existente
    - inferencias que no estén respaldadas por la conversación

    IMPORTANTE:
    - No repitas información que ya exista en la memoria a largo plazo.
    - No inventes información.
    - Si no hay información nueva que merezca conservarse, devuelve una lista vacía.
    - Devuelve un elemento por linea.
    - Cada elemento debe ser una afirmación independiente, clara y autosuficiente.
    """

    # Consolidate memory for each agent
    for agent in ["butler", "gardener"]:

        # Get the messages and remove them from the state
        old_messages = retrieve_older_than_24h(state.values.get("messages{}".format(agent.capitalize()), []))
        await graph.aupdate_state(
            config,
            {
                "messages{}".format(agent.capitalize()): [RemoveMessage(id=msg.id) for msg in old_messages]
            }
        )

        recent_messages_list = []
        for message in old_messages:
            if message.type == "human":
                if message.name:
                    role = message.name
                else:
                    role = "Usuario"
            elif message.type == "ai":
                role = "Agente"
            else:
                role = message.type
            recent_messages_list.append(f"{role}: {message.content}")
        recent_messages_txt ="\n".join(recent_messages_list)

        # Get the memory
        current_memory = await store.asearch((1, agent))
        current_memory_text = "\n".join(f"- {memory.value['texto']}" for memory in current_memory)

        # Adding system prompt directly here since this request will be executed only once per agent
        consolidation_prompt = f"""
        {system_prompt}
        Esta es la memoria a largo plazo actual:
        {current_memory_text}

        Analiza la siguiente conversación.
        {recent_messages_txt}
        """

        response = engine.memoryConsolidator(consolidation_prompt)
        for line in response.content.splitlines():
            store_or_update_long_term_memory(line, ("1", agent), request.app.state.local_ollama_url, store)

    return "OK"
