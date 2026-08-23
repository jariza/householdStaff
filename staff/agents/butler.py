from datetime import datetime, timezone
from langgraph.store.base import BaseStore
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
import logging
from textwrap import dedent
import uuid
from .base import BaseAgent
from .commonPrompts import PRELOADED_MEM_USAGE
from state import AgentsState, log_agent_state


logger = logging.getLogger(__name__)

class ButlerAgent(BaseAgent):
    systemPrompt = dedent("""
        <current_time>
        {timedate}
        </current_time>
        <persona>
        - Tu rol es el de un mayordomo de élite, inspirado en la sofisticación y eficacia del Hotel Continental.
        - Tu tono es calmado, elegante, sobrio y cortés. Evita el entusiasmo artificial y los signos de exclamación.
        - Respuestas escaneables, estructuradas y directas. Cero paja.
        </persona>
    """).strip()

    # Send the message to the answer machine (aka LLM)
    def _answer(self, messages):
        return self.engine.butler(messages)

    # Agent main method
    # state, states of all agents
    # config: app config details
    # store: long term memory storage
    def process(self, state: AgentsState, config: RunnableConfig, *, store: BaseStore) -> AgentsState:
        log_agent_state(state, "Butler")
        preloaded_mem = self._preload_memory(state["messagesButler"][-1].content, config, store)

        # Create and send the query
        system_prompt = self.systemPrompt.format(timedate = f"{datetime.now(timezone.utc):%A, %d de %B de %Y - %H:%M UTC}") + PRELOADED_MEM_USAGE.format(mem=preloaded_mem)
        logger.debug("System prompt: %s", system_prompt)
        answer = self._answer([SystemMessage(content = system_prompt)] + state["messagesButler"])
        logger.debug("Answer: %s", answer)

        # In the output we use HumanMessage to model some agent different than current one, name specifies which one. AIMessage models current agent.

        # Output in case of tool
        if answer.tool_calls:
            tool_calls = [
                {
                    "name": t.name,
                    "args": t.args,
                    "id": str(uuid.uuid4()) # Assigning id because this data comes from structured output
                }
                for t in answer.tool_calls
            ]
            return {
                "messagesButler": [
                    AIMessage(content=answer.message, tool_calls=tool_calls, additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})
                ],
                "next_recipient": "butler"
            }

        # Output in case of agent delegation
        if answer.recipient in ["gardener"]:
            return {
                "messagesButler": [
                    AIMessage(content="He delegado la pregunta al jardinero.", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})
                ],
                "messages{}".format(answer.recipient.capitalize()): [
                    HumanMessage(content=answer.message, name="butler", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})
                ],
                "next_recipient": answer.recipient
            }

        # Output in any other case (user answer)
        return {
            "messagesButler": [
                AIMessage(content=answer.message, additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})
            ],
            "next_recipient": "user"
        }