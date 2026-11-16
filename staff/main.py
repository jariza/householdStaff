import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import tools
from cryptography.fernet import Fernet
from dotenv import dotenv_values
from engines import DebugEngine, LLMEngine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from graph import build_graph
from http_handlers import flow_router, long_term_memory_crud_router
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.tools import BaseTool
from mcp_catalog import MCPSessionManager, populate_mcp_catalog
from persistence import create_persistence_resources

# Get config and data paths
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "config"))
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

# Load and check configuration
config = dotenv_values(CONFIG_DIR / ".env")
FORCED_PERSISTENCE = config.get("FORCED_PERSISTENCE", "none").lower()
DEBUG = config.get("DEBUG", "false").lower() == "true"
TOOLCONFIG_ENCRYPTION_KEY = config.get("TOOLCONFIG_ENCRYPTION_KEY")
GOOGLE_API_KEY = config.get("GOOGLE_API_KEY")
LOCAL_OLLAMA_URL = config.get("LOCAL_OLLAMA_URL")
LOG_LEVEL = config.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_AIOSQLITE = config.get("LOG_LEVEL_AIOSQLITE", "INFO").upper()
LOG_LEVEL_HTTP_CORE = config.get("LOG_LEVEL_HTTP_CORE", "INFO").upper()
NOTIFIER_URL = config.get("NOTIFIER_URL", "http://tgNotif:8001/notify")
STORE_EMBEDDINGS_MODEL = config.get("STORE_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

if not GOOGLE_API_KEY or not LOCAL_OLLAMA_URL or not TOOLCONFIG_ENCRYPTION_KEY:
    raise RuntimeError("Missing variables in .env file: GOOGLE_API_KEY, LOCAL_OLLAMA_URL or TOOLCONFIG_ENCRYPTION_KEY")

# Logging config
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("aiosqlite").setLevel(LOG_LEVEL_AIOSQLITE)

# Prepare store embeddings
store_embeddings = FastEmbedEmbeddings(model_name=STORE_EMBEDDINGS_MODEL)

# Execution context
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:

        engine = DebugEngine() if DEBUG else LLMEngine(api_key=GOOGLE_API_KEY)
        graph = build_graph(engine, CONFIG_DIR)

        persist_memory = DEBUG
        if FORCED_PERSISTENCE == "memory":
            persist_memory = True
        elif FORCED_PERSISTENCE == "db":
            persist_memory = False

        checkpointer, store = await create_persistence_resources(stack, store_embeddings, persist_memory, DATA_DIR)

        # dict with available tools
        available_tools = [func for name, func in tools.__dict__.items() if isinstance(func, BaseTool) and not name.startswith("_")]
        await tools.populate_tool_specs(available_tools, store)

        app.state.graph = graph.compile(checkpointer=checkpointer, store=store)
        app.state.engine = engine
        app.state.local_ollama_url = LOCAL_OLLAMA_URL
        app.state.notifier_url = NOTIFIER_URL
        app.state.store = store
        app.state.mcp_manager = MCPSessionManager(CONFIG_DIR / "mcp_servers.yaml")
        app.state.cipher_suite = Fernet(TOOLCONFIG_ENCRYPTION_KEY.encode())

        await populate_mcp_catalog(CONFIG_DIR / "mcp_servers.yaml", store)

        yield

        await app.state.mcp_manager.close_all()

# FastAPI config
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ['OPTIONS', 'POST', 'GET', 'PUT', 'DELETE']
)
app.include_router(flow_router)
app.include_router(long_term_memory_crud_router)
