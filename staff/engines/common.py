from abc import ABC, abstractmethod
from langchain_core.messages import AIMessage

# Base class for answer engines
class AnswerEngine(ABC):

    @abstractmethod
    def butler(self, messages: list, tools: list | None = None) -> AIMessage:
        ...

    @abstractmethod
    def gardener(self, messages: list, tools: list | None = None) -> AIMessage:
        ...

