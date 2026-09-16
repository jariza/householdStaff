from enum import Enum
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from typing import Annotated
from agents import BaseAgent


AgentName = Enum(
    "AgentName", {
        nombre: nombre.lower()
        for nombre in BaseAgent.delegatable_agents().keys()
    }
)

@tool
def delegar_a_agente(agente_al_que_delegar: AgentName, # type: ignore[reportInvalidTypeForm]
                     mensaje_para_agente_delegado: str, tool_call_id: Annotated[str, InjectedToolCallId]):
    """Delega una tarea a otro agente especializado.
    Utiliza esta herramienta cuando otro agente tenga que realizar una tarea que no debes realizar tú directamente.
    El agente delegado recibirá el mensaje exactamente como se indica y será responsable de ejecutar la tarea. Elige como destinatario únicamente uno de los agentes disponibles.
    """
    return Command(
        # In the output we use HumanMessage to model some agent different than current one, name specifies which one. AIMessage models current agent.

        update={
            "messagesButler": [
                # Inyectamos la confirmación como respuesta a la tool
                ToolMessage(
                    content=f"Tarea derivada al {agente_al_que_delegar.value}: '{mensaje_para_agente_delegado}'",
                    tool_call_id=tool_call_id
                )
            ],
            f"messages{agente_al_que_delegar.value.capitalize()}": [
                # Mensaje de entrada para la cola del jardinero
                HumanMessage(content=mensaje_para_agente_delegado, name="butler")
            ],
            "next_recipient": agente_al_que_delegar.value
        }
    )

