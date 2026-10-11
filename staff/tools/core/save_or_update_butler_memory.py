from langchain_core.messages import ToolMessage
from langgraph.config import get_stream_writer
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from typing import Annotated


@tool
def save_or_update_butler_memory(new_text: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Saves a preference, long-lasting rule, or important detail about the user or household operations.
    USAGE CRITERIA:
    - Use ONLY if the user expresses an explicit preference (e.g., "I prefer concise responses"), an enduring rule or instruction (e.g., "always notify me before making changes"), or an important, stable detail.
    - DO NOT USE for temporary information ("I have guests today"), one-time requests, greetings, or casual conversation.
    """

    # The tool will only request the memory to be updated, the request will be queued as a background task

    # Butler is in the main graph so it uses custom events in this tool
    writer = get_stream_writer()
    writer({
        "type": "memory_update",
        "agent": "butler",
        "new_info": new_text
    })

    return Command(
        update={
            "messagesButler": [
                ToolMessage(
                    content = "Memoria marcada para actualizar.",
                    tool_call_id = tool_call_id
                )
            ]
        }
    )