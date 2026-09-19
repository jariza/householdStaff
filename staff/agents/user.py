from datetime import datetime, timezone
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from state import AgentsState, log_agent_state

# Agent used for user input, it's not a real agent so it only need the process method
class UserInput:
    delegable  = False

    # Agent main method
    # state, states of all agents
    def process(self, state: AgentsState, config: RunnableConfig) -> AgentsState:
        log_agent_state(state, "User")

        user_input = interrupt("Usuario")

        # If it's memory consolidation just pass the flow to the router
        if config.get("configurable", {}).get("memory_consolidation", False):
            return {}

        # It it's not memory consolidation send a message to the butler
        return {
            "messagesButler": [HumanMessage(content=f"{user_input}", name="user", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})]
        }