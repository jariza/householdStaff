from abc import ABC, abstractmethod
from enum import Enum
from langchain_core.messages import AIMessage, BaseMessage

class EngineType(str, Enum):
    NORMAL = "normal"
    SMALL = "small"

# Base class for answer engines
class AnswerEngine(ABC):

    # Extract plain text from a message with block-based content
    @abstractmethod
    def extract_text(self, message: BaseMessage) -> str:
        ...

    @abstractmethod
    async def ainvoke(self, engine_type: EngineType, agent_name: str, messages: list, tools: list | None = None) -> AIMessage:
        ...
