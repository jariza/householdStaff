from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
import logging
import os
from typing import Dict, get_args, List, Optional
import yaml

from agents import CUSTOM_AGENTS, ButlerAgent, GardenerAgent, MemoryConsolidator, UserInput
from httpHandlers import ValidAlertAgents
from state import AgentsState, log_agent_state
import tools

logger = logging.getLogger(__name__)

# Load agent optional tools mapping
def _load_agent_tools_config(config_path: str) -> Dict[str, List[str]]:
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file {config_path} not found. Proceeding with empty optional tool mappings.")
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    return data

# Get the list of tools used by the agent
def _get_tools_for_agent(agent_name: str, available_tools: Dict[str, BaseTool], config_tools_mapping: Dict[str, List[str]], base_tools: Optional[List[str]] = None) -> List[BaseTool]:
    base_tools_list = base_tools or []
    resolved_tools: List[BaseTool] = []
    seen_names = set()

    yaml_tool_names = config_tools_mapping.get(agent_name, [])
    for name in yaml_tool_names + base_tools_list:
        if name not in seen_names:
            seen_names.add(name)
            if name in available_tools:
                resolved_tools.append(available_tools[name])
            else:
                logger.warning(f"Agent {agent_name} requests nonexistent tool: {name}")

    return resolved_tools

# Initial definition
def router_after_user(state: AgentsState, config: RunnableConfig) -> str:
    log_agent_state(state, "Router after User")

    req_type = config.get("configurable", {}).get("req_type", "user")

    if req_type == "consolidate-memory":
        return "memoryConsolidator"
    elif req_type == "alert":
        alert_rcpt = config.get("configurable", {}).get("req_type", "alert_rcpt")
        if alert_rcpt in set(get_args(ValidAlertAgents)):
            return alert_rcpt
        else:
            logger.warning("Not valid alert_rcpt: %s", alert_rcpt)
            return "butler"
    else:
        return "butler"

# Butler router definition
def router_after_butler(state: AgentsState, config: RunnableConfig) -> str:
    allowed_core_agents = ["gardener"]
    allowed_agents = allowed_core_agents + list(CUSTOM_AGENTS.keys())

    # There'll be an empty message the first time the graph runs, it's harmless and fixing it isn't worth the effort
    log_agent_state(state, "Router after Butler")

    last_message_content = state["messagesButler"][-1].content if state["messagesButler"] else ""
    recipient = state.get("next_recipient")

    if isinstance(state["messagesButler"][-1], AIMessage) and state["messagesButler"][-1].tool_calls:
        # Sent to butler's tools node
        destination = "butlerTools"
    elif recipient in allowed_agents:
        # Send to an agent
        destination = recipient
    else:
        # Send to user
        destination = "user"

    logger.debug("Last message received by router_after_butler: %s. Type: %s. Recipient is %s. Will be routed to %s", last_message_content, type(state["messagesButler"][-1]), recipient, destination)
    return destination

# Builds and returns the main graph
# engine, answer engine
def build_graph(engine) -> StateGraph:
    agent_tools_cfg = _load_agent_tools_config("agents_tools.yaml")

    # Base tools
    butler_base_tools = ["delegate_to_agent", "turn_on_garden_light", "search_memory_butler", "save_or_update_butler_memory", "discover_and_load_mcp_butler"]
    gardener_base_tools = ["turn_on_garden_light", "search_memory_gardner", "save_or_update_gardener_memory", "discover_and_load_mcp_gardener"]

    # Dict with available tools
    available_tools = {name: func for name, func in tools.__dict__.items() if isinstance(func, BaseTool) and not name.startswith("_")}

    # Core agents tools
    butler_tools = _get_tools_for_agent("butler", available_tools, agent_tools_cfg, butler_base_tools)
    gardener_tools = _get_tools_for_agent("gardener", available_tools, agent_tools_cfg, gardener_base_tools)

    # Core agents definition
    butler = ButlerAgent(engine, butler_tools)
    gardener = GardenerAgent(engine, gardener_tools)
    memory_consolidator = MemoryConsolidator(engine)
    user=UserInput()

    # Graph definition
    graph = StateGraph(AgentsState)

    # Core nodes definition
    graph.add_node("user", user.process)
    graph.add_node("butler", butler.process)
    graph.add_node("gardener", gardener.process)
    graph.add_node("butlerTools", butler.dynamic_tools_node)
    graph.add_node("memoryConsolidator", memory_consolidator.process)
    
    # Core edges definition
    graph.add_edge(START, "user")
    graph.add_edge("gardener", "butler")
    graph.add_edge("butlerTools", "butler")
    graph.add_edge("memoryConsolidator", "user")
    graph.add_conditional_edges("user", router_after_user)
    graph.add_conditional_edges("butler", router_after_butler)

    # # Custom agents definition
    for agent_name, agent_class in CUSTOM_AGENTS.items():
        custom_agent_tools = _get_tools_for_agent(agent_name, available_tools, agent_tools_cfg)
        agent_instance = agent_class(engine, custom_agent_tools)
        graph.add_node(agent_name, agent_instance.process)
        graph.add_edge(agent_name, "butler")
        logger.info(f"Custom agent {agent_name} loaded")

    return graph
