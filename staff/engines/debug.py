import logging
import uuid

from langchain_core.messages import AIMessage, BaseMessage

from .common import AnswerEngine, EngineType

logger = logging.getLogger(__name__)

# Engine with predictable answers
class DebugEngine(AnswerEngine):

    def extract_text(self, message: BaseMessage) -> str:
        return str(message.content)

    async def ainvoke(self, engine_type: EngineType, agent_name: str, messages: list, tools: list | None = None) -> AIMessage:
        if agent_name == "butler":
            return await self.butler(messages)
        elif agent_name == "gardener":
            return await self.gardener(messages)
        elif agent_name == "memoryConsolidator":
            return await self.memoryConsolidator(messages)
        else:
            return AIMessage(content=f"Parece que el engine no lo está usando un agente previsto: {agent_name}")

    async def butler(self, messages: list) -> AIMessage:
        last_message = messages[-1].content
        logger.debug("Last message in butler status: %s", last_message)

        if last_message == "base":
            return AIMessage(
                content = "Respuestas sin que intervengan otros agentes."
            )
        elif last_message == "jardinero":
            return AIMessage(
                content="Voy a consultar este tema con el jardinero.",
                tool_calls=[{
                    "name": "delegate_to_agent",
                    "args": {"agent_to_delegate_to": "gardener", "message_for_delegated_agent": "Consulta sobre el jardín."},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "tool" or last_message == "Los focos de la zone 'zoneBUTLERMIXTO' del jardin estan encendidos.":
            return AIMessage(
                content="Delego el encendido de luz al jardinero.",
                tool_calls=[{
                    "name": "delegate_to_agent",
                    "args": {"agent_to_delegate_to": "gardener", "message_for_delegated_agent": "encender luz jardin"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "memoriaB":
            return AIMessage(
                content="Voy a actualizar la memoria",
                tool_calls=[{
                    "name": "save_or_update_butler_memory",
                    "args": {"new_text": "cosa mayordomo"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "memoriaG":
            return AIMessage(
                content="Solicito al jardinero actualizar su memoria.",
                tool_calls=[{
                    "name": "delegate_to_agent",
                    "args": {"agent_to_delegate_to": "gardener", "message_for_delegated_agent": "actualizar memoria"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "toolB":
            return AIMessage(
                recipient = "butler",
                content = "Voy a ejecutar la herramienta como butler",
                tool_calls = [{
                    "name": "turn_on_garden_light",
                    "args": {"zone": "zoneBUTLER"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "toolBG":
            return AIMessage(
                recipient = "butler",
                content = "Caso mixto de herrmienta butler",
                tool_calls = [{
                    "name": "turn_on_garden_light",
                    "args": {"zone": "zoneBUTLERMIXTO"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "mcpB":
            return AIMessage(
                recipient = "butler",
                content = "Voy a buscar MCP",
                tool_calls = [{
                    "name": "discover_and_load_mcp_butler",
                    "args": {"search_text": "weather"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "Esto digo como jardinero que soy.":
            return AIMessage(
                content="El jardinero ha dicho cosas."
            )
        else:
            return AIMessage(
                content = f"Respuesta no prevista: {last_message}"
            )

    async def gardener(self, messages: list) -> AIMessage:
        last_message = messages[-1].content
        logger.debug("Last message in gardener status: %s", last_message)

        if last_message == "encender luz jardin":
            return AIMessage(
                content = "Voy a encender la luz de la terraza.",
                tool_calls = [{
                    "name": "turn_on_garden_light",
                    "args": {"zone": "terraza"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "actualizar memoria":
            return AIMessage(
                content = "Soy el jardinero y voy a actualizar la memoria",
                tool_calls = [{
                    "name": "save_or_update_gardener_memory",
                    "args": {"new_text": "cosa jardinero"},
                    "id": str(uuid.uuid4())
                }]
            )
        else:
            return AIMessage(
                content = "Esto digo como jardinero que soy."
            )

    async def memoryConsolidator(self, messages) -> AIMessage:
        last_message = messages[-1].content
        logger.debug("Last message in memory consolidator status: %s", last_message)

        return AIMessage(
            content = "Memoria nueva a añadir"
        )
