from fastapi import Request
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

# Retrieves compiled graph registered in lifespan
def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph

# Retrieves store registered in lifespan
def get_store(request: Request) -> BaseStore:
    return request.app.state.store