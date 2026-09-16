import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse
import httpx
import json
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Command
import logging
from pydantic import BaseModel, Field
from typing import Literal

from longTermMemory import store_or_update_long_term_memory
from state import AgentsState
from .common import get_graph, get_store

logger = logging.getLogger(__name__)

router = APIRouter()

graph_lock = asyncio.Lock() # Will affect only to this module

# Sends message to notification system
async def dispatch_notification(message: str, notifier_url: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(notifier_url, json={"message": message})
        except Exception as e:
            print(f"Couldn't connect to notifier: {e}")

class ChatRequest(BaseModel):
    user_input: str = Field(description = "Request text")
    user_id: str = Field(default="1", description="User ID") # Always 1 until multiuser is considered and implemented
    request_source: Literal["user", "cronjob"] = Field(default="user",  description="Request source")

@router.post("/chat")
async def chat_endpoint(request: Request, data: ChatRequest, background_tasks: BackgroundTasks, graph: CompiledStateGraph = Depends(get_graph), store: BaseStore = Depends(get_store)):

    async def event_generator():
        config = {"configurable": {"thread_id": "1", "user_id": data.user_id}}

        async with graph_lock:
            current_state = await graph.aget_state(config)
        
            if not current_state.values:
                # First time we run the graph
                initial_state = AgentsState(
                    messagesButler=[],
                    messagesGardener=[]
                )
                await graph.ainvoke(initial_state, config)

            user_input_to_send_to_agent = data.user_input
            if data.request_source == "cronjob":
                user_input_to_send_to_agent = (
                    f"[TAREA PROGRAMADA] (El siguiente mensaje proviene de un cronjob automático, adapta tu respuesta según corresponda.)\n{data.user_input}"
                )

            # Run graph and return the answer
            butler_messages: list[str] = []
            async for chunk in graph.astream(Command(resume=user_input_to_send_to_agent), config=config, stream_mode=["updates", "custom"], version="v2"):
                # We are using custom chunks (ephemeral) to notify memory_updates
                if chunk["type"] == "custom":
                    chunk_data = chunk["data"]
                    if chunk_data.get("type") == "memory_update":
                        logger.info("Memory update to sent to background (from %s): %s", chunk_data.get("agent"), chunk_data.get("new_info"))
                        background_tasks.add_task(store_or_update_long_term_memory, chunk_data.get("new_info"), (data.user_id, chunk_data.get("agent")), request.app.state.local_ollama_url, store)
                if chunk["type"] == "updates":
                    for node_name, updates in chunk["data"].items():
                        if node_name == "butler" and "messagesButler" in updates:
                            last_msg = updates['messagesButler'][-1].content
                            butler_messages.append(last_msg)
                            data_payload = json.dumps({"content": last_msg})
                            yield f"data: {data_payload}\n\n"

            # If this request came from a cronjob and the LLM generated a response, send it as a notification
            if data.request_source == "cronjob" and butler_messages:
                full_response = "\n\n".join(butler_messages)
                background_tasks.add_task(dispatch_notification, full_response, request.app.state.notifier_url)

            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")