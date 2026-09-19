from abc import ABC, abstractmethod
from langchain_core.messages import AIMessage, BaseMessage

# Base class for answer engines
class AnswerEngine(ABC):

    # Extract plain text from a message with block-based content
    @abstractmethod
    def extract_text(self, message: BaseMessage) -> str:
        ...

    @abstractmethod
    def butler(self, messages: list, tools: list | None = None) -> AIMessage:
        ...

    @abstractmethod
    def gardener(self, messages: list, tools: list | None = None) -> AIMessage:
        ...

