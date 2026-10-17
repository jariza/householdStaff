import asyncio
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import json
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Command
import logging
from pydantic import BaseModel, Field, field_validator
import re
from typing import get_args, Literal, Optional

from longTermMemory import store_or_update_long_term_memory
from .common import ensure_state_initialized, get_graph, get_store

logger = logging.getLogger(__name__)

router = APIRouter()

graph_lock = asyncio.Lock() # Local to this module

# Sends message to notification system
async def dispatch_notification(message: str, notifier_url: str):
    if "[SILENCIO]" in message.upper():
        silent_notification = True
        message = re.sub(re.escape("[SILENCIO]"), "", message, flags=re.IGNORECASE).strip()
    else:
        silent_notification = False

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(notifier_url, json={"message": message, "silent_notification": silent_notification})
        except Exception as e:
            logger.error(f"Couldn't connect to notifier: {e}")

ValidAlertAgents = Literal["butler", "gardener"]

class ChatRequest(BaseModel):
    user_input: Optional[str] = Field(default=None, description = "Request text")
    user_id: int = Field(default=1, description="User ID") # Always 1 until multiuser is considered and implemented
    alert_rcpt: Optional[str] = Field(default=None, description="Recipient agent in case of alert")

    @field_validator("alert_rcpt")
    @classmethod
    # Same validation than default one but hiding the list of valid options
    def validate_alert_rcpt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in set(get_args(ValidAlertAgents)):
            raise ValueError("Invalid recipient")
        return v

@router.post("/alert")
@router.post("/chat")
@router.post("/consolidate-memory")
async def flow_endpoint(request: Request, background_tasks: BackgroundTasks, data: ChatRequest = Body(default_factory=ChatRequest), graph: CompiledStateGraph = Depends(get_graph), store: BaseStore = Depends(get_store)):
    if request.url.path.endswith("/alert"):
        if not data.alert_rcpt:
            raise HTTPException(status_code=400, detail="alert_rcpt is required when calling /alert")
        if data.alert_rcpt not in set(graph.builder.nodes.keys()):
            raise HTTPException(status_code=400, detail=f"Invalid alert_rcpt {data.alert_rcpt}")
        req_type = "alert"
    elif request.url.path.endswith("/consolidate-memory"):
        req_type = "consolidate-memory"
    else:
        req_type = "user"

    async def event_generator():
        config = {"configurable": {
            "thread_id": "1",
            "user_id": str(data.user_id),
            "req_type": req_type,
            "alert_rcpt": data.alert_rcpt,
            "mcp_manager": request.app.state.mcp_manager
        }}

        async with graph_lock:
            await ensure_state_initialized(graph, config)

            if req_type == "consolidate-memory":
                user_input_to_send_to_agent = ""
            else:
                user_input_to_send_to_agent = data.user_input
                if req_type == "alert":
                    user_input_to_send_to_agent = (
                        f"[ALERTA] (El siguiente mensaje proviene de una alerta automática, adapta tu respuesta según corresponda.)\n{data.user_input}"
                )

            # Run graph and return the answer
            butler_messages: list[str] = []
            async for chunk in graph.astream(Command(resume=user_input_to_send_to_agent), config=config, stream_mode=["updates", "custom"], version="v2"):
                # We are using custom chunks (ephemeral) to notify memory_updates
                if chunk["type"] == "custom":
                    chunk_data = chunk["data"]
                    if chunk_data.get("type") == "memory_update":
                        logger.info("Memory update to sent to background (from %s): %s", chunk_data.get("agent"), chunk_data.get("new_info"))
                        background_tasks.add_task(store_or_update_long_term_memory, chunk_data.get("new_info"), (str(data.user_id), chunk_data.get("agent")), request.app.state.local_ollama_url, store)
                if chunk["type"] == "updates":
                    for node_name, updates in chunk["data"].items():
                        if node_name == "butler" and "messagesButler" in updates:
                            last_msg = updates['messagesButler'][-1]
                            last_msg_text = request.app.state.engine.extract_text(last_msg)
                            if last_msg_text:
                                butler_messages.append(last_msg_text)
                                data_payload = json.dumps({"content": last_msg_text})
                                yield f"data: {data_payload}\n\n"

            # If this request came from a cronjob and the LLM generated a response, send it as a notification
            if req_type == "alert" and butler_messages:
                full_response = "\n\n".join(butler_messages)
                background_tasks.add_task(dispatch_notification, full_response, request.app.state.notifier_url)

            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
