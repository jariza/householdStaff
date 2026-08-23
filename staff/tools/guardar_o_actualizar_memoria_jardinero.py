from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from typing import Annotated

@tool
def guardar_o_actualizar_memoria_jardinero(texto_nuevo: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Guarda una preferencia, regla duradera o dato importante sobre el jardín.
    CRITERIOS DE USO:
    - Usar SOLO si el usuario expresa una preferencia explícita (ej. "me gustan las hortensias"), una norma de la casa (ej. "no regar al mediodía") o un dato permanente.
    - NO USAR para estados temporales ("hoy hace calor"), saludos o conversación trivial.
    """

    # The tool will only request the memory to be updated, the request will be queued as a background task

    return Command(
        update={
            "memories_to_update": [
                {
                    "agent": "gardener",
                    "new_info": texto_nuevo
                }
            ],
            "messages": [
                ToolMessage(
                    content = "Memoria marcada para actualizar.",
                    tool_call_id = tool_call_id
                )
            ]
        }
    )
