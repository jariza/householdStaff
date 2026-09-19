from langgraph.config import get_stream_writer
from langgraph.store.base import BaseStore
from langchain_core.messages import RemoveMessage
import logging
from textwrap import dedent
from state import AgentsState, log_agent_state, retrieve_older_than_24h
from .base import BaseAgent

logger = logging.getLogger(__name__)

# Agent used for memory consolidation
class MemoryConsolidator(BaseAgent):
    delegable  = False

    # Prompt for the memory consolidator
    system_prompt = dedent("""
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
    - No propongas más de 5 líneas.
    """)

    # Agent main method
    # state, states of all agents
    def process(self, state: AgentsState, *, store: BaseStore) -> AgentsState:
        log_agent_state(state, "MemoryConsolidator")

        writer = get_stream_writer()

        updates = {
            "messagesButler": [],
            "messagesGardener": [],
        }

        # Consolidate memory for each agent
        for agent in ["butler", "gardener"]:
            logger.debug("Consolidating %s", agent)

            # Get the messages and remove them from the state
            old_messages = retrieve_older_than_24h(state.get("messages{}".format(agent.capitalize()), []))

            if old_messages:
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
                    updates[f"messages{agent.capitalize()}"].append(RemoveMessage(id=message.id))
                    recent_messages_list.append(f"{role}: {message.content}")

                recent_messages_txt ="\n".join(recent_messages_list)

                # Get the memory
                current_memory = store.search((1, agent))
                current_memory_text = "\n".join(f"- {memory.value['texto']}" for memory in current_memory)

                # Adding system prompt directly here since this request will be executed only once per agent
                prompt_template = dedent("""
                    {}
                    Esta es la memoria a largo plazo actual:
                    {}

                    Analiza la siguiente conversación.
                    {}
                    """)
                # Templating the prompt in two steps so there are no issues with indent in the final prompt
                consolidation_prompt = prompt_template.format(self.system_prompt, current_memory_text, recent_messages_txt)

                response = self.engine.memoryConsolidator(consolidation_prompt)
                if response.content:
                    writer({
                        "type": "memory_update",
                        "agent": agent,
                        "new_info": response.content,
                    })

        return updates