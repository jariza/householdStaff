from contextlib import asynccontextmanager, AsyncExitStack
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from langchain_community.embeddings import FastEmbedEmbeddings

from engines import DebugEngine, LLMEngine
from graph import build_graph
from httpHandlers import chat_router, consolidate_memory_router, long_term_memory_crud_router
from tools import buscar_memoria_jardinero, buscar_memoria_mayordomo, delegar_a_agente, encender_luz_jardin, guardar_o_actualizar_memoria_mayordomo, guardar_o_actualizar_memoria_jardinero
from persistence import create_persistence_resources

# Load and check configuration
config = dotenv_values(".env")
DEBUG = config.get("DEBUG", "false").lower() == "true"
LOCAL_OLLAMA_URL = config.get("LOCAL_OLLAMA_URL")
LOG_LEVEL = config.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_AIOSQLITE = config.get("LOG_LEVEL_AIOSQLITE", "INFO").upper()
NOTIFIER_URL = config.get("NOTIFIER_URL")
STORE_EMBEDDINGS_MODEL = config.get("STORE_EMBEDDINGS_MODEL")

if not LOCAL_OLLAMA_URL or not NOTIFIER_URL or not STORE_EMBEDDINGS_MODEL:
    raise RuntimeError("Missing variables in .env file: LOCAL_OLLAMA_URL, NOTIFIER_URL or STORE_EMBEDDINGS_MODEL")

# Logging config
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("aiosqlite").setLevel(LOG_LEVEL_AIOSQLITE)

# Agents tools and engine
gardener_tools = [encender_luz_jardin, buscar_memoria_jardinero, guardar_o_actualizar_memoria_jardinero]
butler_tools = [delegar_a_agente, encender_luz_jardin, buscar_memoria_mayordomo, guardar_o_actualizar_memoria_mayordomo]

# Prepare store embeddings
store_embeddings = FastEmbedEmbeddings(model_name=STORE_EMBEDDINGS_MODEL)

# Execution context
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:

        engine = DebugEngine() if DEBUG else LLMEngine()
        graph = build_graph(engine, butler_tools, gardener_tools)

        checkpointer, store = await create_persistence_resources(stack, store_embeddings, DEBUG)
        app.state.graph = graph.compile(checkpointer=checkpointer, store=store)
        app.state.engine = engine
        app.state.local_ollama_url = LOCAL_OLLAMA_URL
        app.state.notifier_url = NOTIFIER_URL
        app.state.store = store

        yield

# FastAPI config
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ['OPTIONS', 'POST', 'GET', 'PUT', 'DELETE']
)
app.include_router(chat_router)
app.include_router(consolidate_memory_router)
app.include_router(long_term_memory_crud_router)
