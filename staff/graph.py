from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
import logging

from agents import ButlerAgent, GardenerAgent, MemoryConsolidator, UserInput
from state import AgentsState, log_agent_state

logger = logging.getLogger(__name__)

# Initial definition
def router_after_user(state: AgentsState, config: RunnableConfig) -> str:
    log_agent_state(state, "Router after User")

    if config.get("configurable", {}).get("memory_consolidation", False):
        return "memoryConsolidator"
    else:
        return "butler"

# Butler router definition
def router_after_butler(state: AgentsState, config: RunnableConfig) -> str:
    # There'll be an empty message the first time the graph runs, it's harmless and fixing it isn't worth the effort
    log_agent_state(state, "Router after Butler")

    last_message_content = state["messagesButler"][-1].content if state["messagesButler"] else ""
    recipient = state.get("next_recipient")

    if isinstance(state["messagesButler"][-1], AIMessage) and state["messagesButler"][-1].tool_calls:
        # Sent to butler's tools node
        destination = "butlerTools"
    elif recipient in ["gardener"]:
        # Send to an agent
        destination = recipient
    else:
        # Send to user
        destination = "user"

    logging.debug("Last message received by router_after_butler: %s. Type: %s. Recipient is %s. Will be routed to %s", last_message_content, type(state["messagesButler"][-1]), recipient, destination)
    return destination

# Builds and returns the main graph
# engine, answer engine
# butler_tools, tools used by butler
# gardener_tools, tools used by gardener
def build_graph(engine, butler_tools, gardener_tools) -> StateGraph:
    # Agents definition
    butler = ButlerAgent(engine, butler_tools)
    gardener = GardenerAgent(engine, gardener_tools)
    memory_consolidator = MemoryConsolidator(engine)
    user=UserInput()

    # Graph definition
    graph = StateGraph(AgentsState)
    # Nodes

    graph.add_node("user", user.process)
    graph.add_node("butler", butler.process)
    graph.add_node("gardener", gardener.process)
    graph.add_node("butlerTools", ToolNode(butler_tools, messages_key="messagesButler"))
    graph.add_node("memoryConsolidator", memory_consolidator.process)
    # Edges
    graph.add_edge(START, "user")
    graph.add_edge("gardener", "butler")
    graph.add_edge("butlerTools", "butler")
    graph.add_edge("memoryConsolidator", "user")
    graph.add_conditional_edges("user", router_after_user)
    graph.add_conditional_edges("butler", router_after_butler)

    return graph
