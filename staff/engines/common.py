from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Literal

# Structured agent response
class AgentResponse(BaseModel):
    recipient: Literal["user", "butler", "gardener"] = Field(
        description = "Actor destinatario del mensaje a enviar"
    )
    message: str = Field(
        description = "Mensaje o explicación a enviar al actor destinatario"
    )
    tool_calls: list[ToolCall] = Field(
        default_factory = list,
        description = "Herramientas que el Butler solicita ejecutar. Vacía cuando no necesita ejecutar ninguna herramienta."
    )

# Data structure for tool calls
class ToolCall(BaseModel):
    name: str = Field(
        description = "Nombre exacto de la herramienta que se debe ejecutar."
    )
    args: dict[str, Any] = Field(
        default_factory = dict,
        description = "Argumentos que se deben proporcionar a la herramienta."
    )

# Base class for answer engines
class AnswerEngine(ABC):

    @abstractmethod
    def butler(self, messages) -> AgentResponse:
        ...

    @abstractmethod
    def gardener(self, messages) -> AgentResponse:
        ...

