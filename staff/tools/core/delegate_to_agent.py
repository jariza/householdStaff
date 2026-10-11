from enum import Enum
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from typing import Annotated
from agents import BaseAgent


AgentName = Enum(
    "AgentName", {
        name: name.lower()
        for name in BaseAgent.delegatable_agents().keys()
    }
)

@tool
def delegate_to_agent(agent_to_delegate_to: AgentName, # type: ignore[reportInvalidTypeForm]
                     message_for_delegated_agent: str, tool_call_id: Annotated[str, InjectedToolCallId]):
    """Delegates a task to another specialized agent.
    Use this tool when another agent must perform a task that you should not execute directly.
    The delegated agent will receive the message exactly as provided and will be responsible for executing the task. Choose as recipient only one of the available agents.
    """
    return Command(
        # In the output we use HumanMessage to model some agent different than current one, name specifies which one. AIMessage models current agent.

        update={
            "messagesButler": [
                # Inject the confirmation as a response to the tool
                ToolMessage(
                    content=f"Tarea derivada al {agent_to_delegate_to.value}: '{message_for_delegated_agent}'",
                    tool_call_id=tool_call_id
                )
            ],
            f"messages{agent_to_delegate_to.value.capitalize()}": [
                # Input message for the gardener queue
                HumanMessage(content=message_for_delegated_agent, name="butler")
            ],
            "next_recipient": agent_to_delegate_to.value
        }
    )
