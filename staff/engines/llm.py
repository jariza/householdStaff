from langchain_core.messages import AIMessage
from .common import AnswerEngine

# Engine with real LLMs
class LLMEngine(AnswerEngine):

    def butler(self, messages: list, tools: list | None = None) -> AIMessage:
        return

    def gardener(self, messages: list, tools: list | None = None) -> AIMessage:
        return