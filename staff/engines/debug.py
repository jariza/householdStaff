from langchain_core.messages import AIMessage
import logging
import uuid
from .common import AnswerEngine

logger = logging.getLogger(__name__)

# Engine with predictable answers
class DebugEngine(AnswerEngine):

    def butler(self, messages: list, tools: list | None = None) -> AIMessage:
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
                    "name": "delegar_a_agente",
                    "args": {"agente_al_que_delegar": "gardener", "mensaje_para_agente_delegado": "Consulta sobre el jardín."},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "tool" or last_message == "Los focos de la zona 'ZONABUTLERMIXTO' del jardin estan encendidos.":
            return AIMessage(
                content="Delego el encendido de luz al jardinero.",
                tool_calls=[{
                    "name": "delegar_a_agente",
                    "args": {"agente_al_que_delegar": "gardener", "mensaje_para_agente_delegado": "encender luz jardin"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "memoriaB":
            return AIMessage(
                content="Voy a actualizar la memoria",
                tool_calls=[{
                    "name": "guardar_o_actualizar_memoria_mayordomo",
                    "args": {"texto_nuevo": "cosa mayordomo"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "memoriaG":
            return AIMessage(
                content="Solicito al jardinero actualizar su memoria.",
                tool_calls=[{
                    "name": "delegar_a_agente",
                    "args": {"agente_al_que_delegar": "gardener", "mensaje_para_agente_delegado": "actualizar memoria"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "toolB":
            return AIMessage(
                recipient = "butler",
                content = "Voy a ejecutar la herramienta como butler",
                tool_calls = [{
                    "name": "encender_luz_jardin",
                    "args": {"zona": "ZONABUTLER"},
                    "id": str(uuid.uuid4())
                }]
            )
        elif last_message == "toolBG":
            return AIMessage(
                recipient = "butler",
                content = "Caso mixto de herrmienta butler",
                tool_calls = [{
                    "name": "encender_luz_jardin",
                    "args": {"zona": "ZONABUTLERMIXTO"},
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

    def gardener(self, messages: list, tools: list | None = None) -> AIMessage:
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
