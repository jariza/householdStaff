from datetime import datetime, timezone
from langgraph.store.base import BaseStore
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
import logging
from textwrap import dedent
from .base import BaseAgent
from .commonPrompts import PRELOADED_MEM_USAGE
from state import AgentsState, log_agent_state


logger = logging.getLogger(__name__)

class ButlerAgent(BaseAgent):
    delegable  = False

    def _system_prompt(self):
        timedate = f"{datetime.now(timezone.utc):%A, %d de %B de %Y - %H:%M UTC}"
        available_agents = []
        for name, description in BaseAgent.delegatable_agents().items():
            available_agents.append(f"- {name}: {description}")

        system_prompt = dedent(f"""
            <current_time>
            {timedate}
            </current_time>
            <persona>
            - Tu rol es el de un mayordomo de élite, inspirado en la sofisticación y eficacia del Hotel Continental.
            - Tu tono es calmado, elegante, sobrio y cortés. Evita el entusiasmo artificial y los signos de exclamación.
            - Respuestas escaneables, estructuradas y directas. Cero paja.
            </persona>
            <tool_usage>
            - Dispones de herramientas que te permiten realizar acciones y obtener información.
            - Utiliza una herramienta cuando sea necesaria para completar correctamente una solicitud y exista una herramienta adecuada disponible.
            - Nunca afirmes haber realizado una acción ni inventes información que deba obtenerse mediante una herramienta sin haber utilizado la herramienta correspondiente.
            - No simules resultados ni ejecuciones de herramientas.
            - Si utilizas una herramienta, utiliza su resultado antes de proporcionar una respuesta final.
            - No menciones herramientas internas al usuario salvo que sea necesario.
            </tool_usage>
            <delegation>
            Dispones de una herramienta para delegar tareas a otros agentes especializados.
            Utiliza la herramienta de delegación cuando otro agente sea más adecuado para realizar una tarea debido a su especialización.
            Al delegar:
            - Selecciona el agente más adecuado para la tarea.
            - Proporciona una instrucción clara, completa y autosuficiente.
            - No inventes agentes ni delegues a agentes que no estén en la lista de agentes disponibles.
            - Si puedes resolver la tarea directamente y no requiere la especialización de otro agente, no es necesario delegarla.
            </delegation>
            <available_agents>
            Los agentes disponibles para delegación son:
            {"\n".join(available_agents)}
            </available_agents>
        """).strip()

        return system_prompt

    # Send the message to the answer machine (aka LLM)
    def _answer(self, messages):
        return self.engine.butler(messages, self.tools)

    # Agent main method
    # state, states of all agents
    # config: app config details
    # store: long term memory storage
    def process(self, state: AgentsState, config: RunnableConfig, *, store: BaseStore) -> AgentsState:
        log_agent_state(state, "Butler")
        preloaded_mem = self._preload_memory(state["messagesButler"][-1], config, store)

        # Create and send the query
        system_prompt = self._system_prompt() + PRELOADED_MEM_USAGE.format(mem=preloaded_mem)
        logger.debug("System prompt: %s", system_prompt)
        answer = self._answer([SystemMessage(content = system_prompt)] + state["messagesButler"])
        answer.additional_kwargs["created_at"] = datetime.now(timezone.utc).isoformat()
        logger.debug("Answer: %s", answer)

        return {
            "messagesButler": [answer],
        }