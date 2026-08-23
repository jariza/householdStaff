from langchain_core.messages import AIMessage
from .common import AgentResponse, AnswerEngine

# Engine with real LLMs
class LLMEngine(AnswerEngine):

    def butler(self, messages) -> AgentResponse:
        return

    def gardener(self, messages) -> AIMessage:
        return