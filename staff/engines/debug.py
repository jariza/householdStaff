from langchain_core.messages import AIMessage
import logging
import uuid
from .common import AgentResponse, AnswerEngine

logger = logging.getLogger(__name__)

# Engine with predictable answers
class DebugEngine(AnswerEngine):

    def butler(self, message) -> AgentResponse:
        last_message = message[-1].content
        logger.debug("Last message in butler status: %s", last_message)

        if last_message == "base":
            return AgentResponse(
                recipient = "user",
                message = "Respuestas sin que intervengan otros agentes."
            )
        elif last_message == "jardinero":
            return AgentResponse(
                recipient = "gardener",
                message = "Consulta sobre el jardín."
            )
        elif last_message == "tool" or last_message == "Los focos de la zona 'ZONABUTLERMIXTO' del jardin estan encendidos.":
            return AgentResponse(
                recipient = "gardener",
                message = "encender luz jardin"
            )
        elif last_message == "memoriaB":
            return AgentResponse(
                recipient = "butler",
                message = "Voy a actualizar la memoria",
                tool_calls = [{
                    "name": "guardar_o_actualizar_memoria_mayordomo",
                    "args": {"texto_nuevo": "cosa mayordomo"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "memoriaG":
            return AgentResponse(
                recipient = "gardener",
                message = "actualizar memoria"
            )
        elif last_message == "toolB":
            return AgentResponse(
                recipient = "butler",
                message = "Voy a ejecutar la herramienta como butler",
                tool_calls = [{
                    "name": "encender_luz_jardin",
                    "args": {"zona": "ZONABUTLER"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "toolBG":
            return AgentResponse(
                recipient = "butler",
                message = "Caso mixto de herrmienta butler",
                tool_calls = [{
                    "name": "encender_luz_jardin",
                    "args": {"zona": "ZONABUTLERMIXTO"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "Esto digo como jardinero que soy.":
            return AgentResponse(
                recipient = "user",
                message = "El jardinero ha dicho cosas."
            )
        else:
            return AgentResponse(
                recipient = "user",
                message = f"Respuesta no prevista: {last_message}"
            )

    def gardener(self, messages) -> AIMessage:
        last_message = messages[-1].content
        logger.debug("Last message in gardener status: %s", last_message)

        if last_message == "encender luz jardin":
            return AIMessage(
                content = "Voy a encender la luz de la terraza.",
                tool_calls = [{
                    "name": "encender_luz_jardin",
                    "args": {"zona": "terraza"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "actualizar memoria":
            return AIMessage(
                content = "Soy el jardinero y voy a actualizar la memoria",
                tool_calls = [{
                    "name": "guardar_o_actualizar_memoria_jardinero",
                    "args": {"texto_nuevo": "cosa jardinero"},
                    "id": str(uuid.uuid4())
                }]
            )
        else:
            return AIMessage(
                content = "Esto digo como jardinero que soy."
            )

    def memoryConsolidator(self, messages) -> AIMessage:
        print(messages)
        last_message = messages[-1]
        logger.debug("Last message in memory consolidator status: %s", last_message)

        return AIMessage(
            content = "Memoria nueva a añadir"
        )
