from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
from .common import AnswerEngine

logger = logging.getLogger(__name__)

# Engine with real LLMs
class LLMEngine(AnswerEngine):

    def __init__(self, api_key: str):
        # Models should be listed in decreasing preference order
        butler_models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-2-flash"] #"gemini-3.8-flash", "gemini-3.7-flash", 
        small_agent_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]

        # Prepare models
        butler_llms = [
            ChatGoogleGenerativeAI(model=name, api_key=api_key, temperature=0.2, max_retries=1)
            for name in butler_models
        ]
        primary_butler_llm = butler_llms[0]
        fallback_butler_llms = butler_llms[1:]

        small_agent_llms = [
            ChatGoogleGenerativeAI(model=name, api_key=api_key, temperature=0.2, max_retries=1)
            for name in small_agent_models
        ]
        primary_small_agent_llm = small_agent_llms[0]
        fallback_small_agent_llms = small_agent_llms[1:]

        # Assign model to agent
        self.butler_llm = primary_butler_llm.with_fallbacks(fallback_butler_llms)
        self.gardener_llm = primary_small_agent_llm.with_fallbacks(fallback_small_agent_llms)
    
    def extract_text(self, message: BaseMessage) -> str:
        content = message.content

        # Content is a string
        if isinstance(content, str):
            return content

        # Structured content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict):
                    if block.get("type") == "text":
                        text = block.get("text")
                        if text:
                            text_parts.append(text)
            return "".join(text_parts)

        # Fallback
        return str(content)


    def butler(self, messages: list, tools: list | None = None) -> AIMessage:
        try:
            butler_tooled_llm = self.butler_llm
            if tools:
                butler_tooled_llm = butler_tooled_llm.bind_tools(tools)
            response = butler_tooled_llm.invoke(messages)
            return response
        except Exception:
            logger.exception("All butler LLMs have failed:")
            return AIMessage(
                message = "Lo siento, en este momento no puedo procesar tu solicitud debido a un problema técnico de conexión."
            )

    def gardener(self, messages: list, tools: list | None = None) -> AIMessage:
        try:
            gardener_tooled_llm = self.gardener_llm
            if tools:
                gardener_tooled_llm = gardener_tooled_llm.bind_tools(tools)
            response = gardener_tooled_llm.invoke(messages)
            logger.debug("Gardener LLM answer: %s", response)
            return response
        except Exception:
            logger.exception("All gardener LLMs have failed:")
            return AIMessage(
                content = "Lo siento, en este momento no puedo procesar tu solicitud debido a un problema técnico de conexión."
            )
