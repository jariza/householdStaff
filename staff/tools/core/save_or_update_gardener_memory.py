from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from typing import Annotated

@tool
def save_or_update_gardener_memory(new_text: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Saves a preference, long-lasting rule, or important detail about the garden.
    USAGE CRITERIA:
    - Use ONLY if the user expresses an explicit preference (e.g., "I like hydrangeas"), a house rule (e.g., "do not water at noon"), or a permanent fact.
    - DO NOT USE for temporary states ("it is hot today"), greetings, or casual conversation.
    """

    # The tool will only request the memory to be updated, the request will be queued as a background task

    return Command(
        update={
            "memories_to_update": [
                {
                    "agent": "gardener",
                    "new_info": new_text
                }
            ],
            "messages": [
                ToolMessage(
                    content = "Memoria marcada para actualizar.",
                    tool_call_id = tool_call_id
                )
            ]
        }
    )
