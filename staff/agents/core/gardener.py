from datetime import datetime, timezone
from langgraph.config import get_stream_writer
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore
from langgraph.types import Command
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
import logging
from operator import add
from textwrap import dedent
from typing import Annotated, TypedDict

from ..base import BaseAgent
from ..commonPrompts import PRELOADED_MEM_USAGE
from engines import EngineType
from mcp_catalog import search_server_mcp_catalog
from state import AgentsState, log_agent_state

logger = logging.getLogger(__name__)

class LongTermMemoryUpdate(TypedDict):
    agent: str
    new_info: str

class GardenerAgent(BaseAgent):
    description = "Especialista en jardinería, plantas y cuidado del jardín."

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
        <tool_usage>
        - Dispones de herramientas que te permiten realizar acciones y obtener información.
        - Algunas tools proceden de MCP; si consideras que las herramientas activas son insuficientes, dispones de herramientas para buscar y cargar más tools.
        - Las herramientas MCP disponibles pueden cambiar dinámicamente entre mensajes. No asumas que una herramienta del historial sigue activa si no figura en tu lista actual de tools.
        - Utiliza una herramienta cuando sea necesaria para completar correctamente una solicitud y exista una herramienta adecuada disponible.
        - Nunca afirmes haber realizado una acción ni inventes información que deba obtenerse mediante una herramienta sin haber utilizado la herramienta correspondiente.
        - No simules resultados ni ejecuciones de herramientas.
        - Si utilizas una herramienta, utiliza su resultado antes de proporcionar una respuesta final.
        - No menciones herramientas internas al usuario salvo que sea necesario.
        </tool_usage>
    """).strip()

    # Local state used in the subgraph
    # This state is not persisted so we don't need to take care of cleaning memories_to_update
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        memories_to_update: Annotated[list[LongTermMemoryUpdate], add]
        mcp_server_in_use: list[str]

    # Initialization
    # Adds subgraph to the base
    def __init__(self, engine, base_tools: list[BaseTool]):
        super().__init__(engine, base_tools)
        self.subgraph = self._build_subgraph()

    async def _search_for_useful_mcp(self, state: State, store: BaseStore):
        last_message = self.engine.extract_text(state["messages"][-1])

        mcp_server = await search_server_mcp_catalog(last_message, store)
        if (mcp_server) and (mcp_server not in state["mcp_server_in_use"]):
            state["mcp_server_in_use"].append(mcp_server)

    # Agent node for the subgraph
    # state, internal state
    # config: app config details
    # store: long term memory storage
    async def _agent_node(self, state: State, config: RunnableConfig, *, store: BaseStore) -> State:
        log_agent_state(state, "Gardener")
        preloaded_mem = await self._preload_memory(state["messages"][-1], config, store)
        await self._search_for_useful_mcp(state, store)

        # Create and send the query
        system_prompt = self.systemPrompt.format(timedate = f"{datetime.now(timezone.utc):%A, %d de %B de %Y - %H:%M UTC}") + PRELOADED_MEM_USAGE.format(mem=preloaded_mem)
        logger.debug("System prompt: %s", system_prompt)
        active_tools = await self._get_active_tools(state["mcp_server_in_use"], config)
        answer = await self.engine.ainvoke(EngineType.SMALL, "gardener", [SystemMessage(content = system_prompt)] + state["messages"], active_tools)
        logger.debug("Answer: %r", answer)

        return {"messages": [answer]}

    # Allows tool node to change the set of tools
    async def _dynamic_tools_node(self, state: State, config: RunnableConfig):
        active_tools = await self._get_active_tools(state["mcp_server_in_use"], config)
        executor = ToolNode(active_tools)
        return await executor.ainvoke(state, config)

    # Creates the subgraph
    def _build_subgraph(self) -> CompiledStateGraph:
        agent_subgraph = StateGraph(self.State)

        agent_subgraph.add_node("gardener", self._agent_node)
        agent_subgraph.add_node("tools", self._dynamic_tools_node)

        agent_subgraph.add_edge(START, "gardener")
        agent_subgraph.add_conditional_edges("gardener", tools_condition) # Conditional edge: if there is any tool run it, END if there is no tool
        agent_subgraph.add_edge("tools", "gardener")

        return agent_subgraph.compile()

    # Agent main method
    # state, internal state
    async def process(self, state: AgentsState) -> AgentsState:
        last_butler_msg = state["messagesGardener"][-1].content
        logger.debug("Las message from butler: %s", last_butler_msg)

        # We use HumanMessage to model some agent different than current one, name specifies which one. AIMessage models current agent.
        subgraph_result = await self.subgraph.ainvoke({
            "messages": [HumanMessage(content=last_butler_msg, name="butler")],
            "memories_to_update": [],
            "mcp_server_in_use": []
        })

        # Transform memory_to_update into customs so tasks are sent to background tasks
        writer = get_stream_writer()
        for memory_update in subgraph_result.get("memories_to_update", []):
            writer({"type": "memory_update", "agent": memory_update["agent"], "new_info": memory_update["new_info"]})

        final_msg = subgraph_result["messages"][-1]
        final_msg.additional_kwargs["created_at"] = datetime.now(timezone.utc).isoformat()
        logger.debug("Final message from gardener: %s", final_msg)

        return Command(
            update={
                "messagesButler": [HumanMessage(content=final_msg.content, name="gardener", additional_kwargs={"created_at": datetime.now(timezone.utc).isoformat()})],
                "messagesGardener": final_msg,
                "memories_to_update": subgraph_result.get("memories_to_update", []),
                "next_recipient": None # Not required since final answer from agents always goes to butler
            }
        )