from datetime import datetime, timezone
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore
from langgraph.types import Command
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
import logging
from operator import add
from textwrap import dedent
from typing import Annotated, TypedDict
from .base import BaseAgent
from .commonPrompts import PRELOADED_MEM_USAGE
from state import AgentsState, log_agent_state, LongTermMemoryUpdate

logger = logging.getLogger(__name__)

class GardenerAgent(BaseAgent):
    # This agent uses a subgraph with two nodes:
    # - agent itself
    # - tools node
    # The state is non permanent

    systemPrompt = dedent("""
        <current_time>
        {timedate}
        </current_time>
        <persona>
        - Eres el especialista botánico y jardinero principal de la propiedad.
        - Tu tono es profesional, sobrio, observador y eminentemente práctico.
        - Respuestas claras, enfocadas en la salud de las plantas, condiciones climáticas y mantenimiento del jardín.
        </persona>
    """).strip()

    # Local state used in the subgraph
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        memories_to_update: Annotated[list[LongTermMemoryUpdate], add]

    # Initialization
    # Adds tools and subgraph to the base
    # tools, list of tool to bind the the agent
    def __init__(self, engine, tools):
        super().__init__(engine)
        self.tools = tools
        self.subgraph = self._build_subgraph()

    # Send the message to the answer machine (aka LLM)
    def _answer(self, messages):
        return self.engine.gardener(messages)

    # Agent node for the subgraph
    # state, internal state
    # config: app config details
    # store: long term memory storage
    def _agent_node(self, state: State, config: RunnableConfig, *, store: BaseStore) -> State:
        log_agent_state(state, "Gardener")
        preloaded_mem = self._preload_memory(state["messages"][-1].content, config, store)

        # Create and send the query
        system_prompt = self.systemPrompt.format(timedate = f"{datetime.now(timezone.utc):%A, %d de %B de %Y - %H:%M UTC}") + PRELOADED_MEM_USAGE.format(mem=preloaded_mem)
        logger.debug("System prompt: %s", system_prompt)
        answer = self._answer([SystemMessage(content = system_prompt)] + state["messages"])
        logger.debug("Answer: %s", answer)

        return {"messages": [answer]}

    # Creates the subgraph
    def _build_subgraph(self) -> CompiledStateGraph:
        agent_subgraph = StateGraph(self.State)

        agent_subgraph.add_node("gardener", self._agent_node)
        agent_subgraph.add_node("tools", ToolNode(self.tools))

        agent_subgraph.add_edge(START, "gardener")
        agent_subgraph.add_conditional_edges("gardener", tools_condition) # Conditional edge: if there is any tool run it, END if there is no tool
        agent_subgraph.add_edge("tools", "gardener")

        return agent_subgraph.compile()

    # Agent main method
    # state, internal state
    def process(self, state: AgentsState) -> AgentsState:
        last_butler_msg = state["messagesGardener"][-1].content
        logger.debug("Las message from butler: %s", last_butler_msg)

        # We use HumanMessage to model some agent different than current one, name specifies which one. AIMessage models current agent.
        subgraph_result = self.subgraph.invoke({"messages": [HumanMessage(content=last_butler_msg, name="butler")]})
        final_msg = subgraph_result["messages"][-1].content
        logger.debug("Final message from gardener: %s", final_msg)

        return Command(
            update={
                "messagesButler": [HumanMessage(content=final_msg, name="gardener", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})],
                "memories_to_update": subgraph_result.get("memories_to_update", []),
                "next_recipient": None # Not required since final answer from agents always goes to butler
            }
        )