from datetime import datetime, timezone
from langgraph.types import interrupt
from langchain_core.messages import HumanMessage
from state import AgentsState, log_agent_state

# Agent used for user input, it's not a real agent so it only need the process method
class UserInput:

    # Agent main method
    # state, states of all agents
    def process(self, state: AgentsState) -> AgentsState:
        log_agent_state(state, "User")
        user_input = interrupt("Usuario")
        return {
            "messagesButler": [HumanMessage(content=f"{user_input}", name="user", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})]
        }