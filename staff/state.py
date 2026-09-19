from datetime import datetime, timedelta, timezone
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import logging
from typing import Annotated, TypedDict

logger = logging.getLogger(__name__)

# Formatted log of agents states
# state, agents states
# title, message header
def log_agent_state(state: AgentsState, title: str):
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

    lines.append("=" * 54)

    logger.debug("%s", "\n".join(lines))

# States for agents and who is going to receive the next message (next_recipient)
class AgentsState(TypedDict):
    messagesButler: Annotated[list[BaseMessage], add_messages]
    messagesGardener: Annotated[list[BaseMessage], add_messages]
    next_recipient: str | None

# Return status message older than 24h
def retrieve_older_than_24h(messages: list) -> list:
    # twentyfour_h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    # TODO: para prueba, eliminar luego
    twentyfour_h_ago = datetime.now(timezone.utc)

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