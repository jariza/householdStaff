import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

# States for agents and who is going to receive the next message (next_recipient)
class AgentsState(TypedDict):
    messagesButler: Annotated[list[BaseMessage], add_messages]
    messagesGardener: Annotated[list[BaseMessage], add_messages]
    mcpServersInUseByButler: list[str]
    next_recipient: str | None

# Formatted log of agents states
# state, agents states
# title, message header
def log_agent_state(state: AgentsState, title: str):
    if not logger.isEnabledFor(logging.DEBUG):
        return

    lines = ["", f"==================== {title} ===================="]

    for channel in ("messagesButler", "messagesGardener"):
        messages = state.get(channel, [])

        lines.append(f"{channel} ({len(messages)} messages)")

        for i, msg in enumerate(messages):
            message_type = type(msg).__name__
            icon = (
                "👤" if message_type == "HumanMessage"
                else "🤖" if message_type == "AIMessage"
                else "⚙️"
            )
            content = str(msg.content).replace("\n", " ")
            name = getattr(msg, "name", None) or "-"
            lines.append(f"  [{i}] {icon} {message_type} de {name}: {content}")

    next_recipient = state.get("next_recipient")
    lines.append(f"next_recipient: {next_recipient!r}")

    mcpServersInUseByButler = state.get("mcpServersInUseByButler")
    lines.append(f"mcpServersInUseByButler: {mcpServersInUseByButler!r}")

    lines.append("=" * 54)

    logger.debug("%s", "\n".join(lines))

# Return status message older than 24h
def retrieve_older_than_24h(messages: list) -> list:
    twentyfour_h_ago = datetime.now(UTC) - timedelta(hours=24)

    old_messages = []

    for msg in messages:
        created_at_str = msg.additional_kwargs.get("created_at")
        
        if created_at_str:
            msg_date = datetime.fromisoformat(created_at_str)
            
            if msg_date < twentyfour_h_ago:
                old_messages.append(msg)
        else:
            logger.error("Message without create_at, ignored: %s", msg)

    return old_messages