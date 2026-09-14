from langchain_core.messages import ToolMessage
from langgraph.config import get_stream_writer
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from typing import Annotated


@tool
def guardar_o_actualizar_memoria_mayordomo(texto_nuevo: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Guarda una preferencia, regla duradera o dato importante sobre el usuario o el funcionamiento de la casa.
    CRITERIOS DE USO:
    - Usar SOLO si el usuario expresa una preferencia explícita (ej. "prefiero que me hables de forma breve"), una norma o instrucción duradera (ej. "avísame siempre antes de hacer cambios") o un dato importante y estable.
    - NO USAR para información temporal ("hoy tengo invitados"), solicitudes puntuales, saludos o conversación trivial.
    """

    # The tool will only request the memory to be updated, the request will be queued as a background task

    # Butler is in the main graph so it uses custom events in this tool
    writer = get_stream_writer()
    writer({
        "type": "memory_update",
        "agent": "butler",
        "new_info": texto_nuevo
    })

    return Command(
        update={
            "messagesButler": [
                ToolMessage(
                    content = "Memoria marcada para actualizar.",
                    tool_call_id = tool_call_id
                )
            ]
        }
    )