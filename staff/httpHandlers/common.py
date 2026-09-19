from fastapi import Request
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from state import AgentsState

# Retrieves compiled graph registered in lifespan
def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph

# Retrieves store registered in lifespan
def get_store(request: Request) -> BaseStore:
    return request.app.state.store

# Ensures the state was initialized
async def ensure_state_initialized(graph, config):
    state = await graph.aget_state(config)

    if not state.values:
        # First time we run the graph
        initial_state = AgentsState(
            messagesButler = [],
            messagesGardener = []
        )
        await graph.ainvoke(initial_state, config)
