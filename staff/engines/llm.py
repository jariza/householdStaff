from langchain_core.messages import AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
from .common import AnswerEngine, EngineType

logger = logging.getLogger(__name__)

# Engine with real LLMs
class LLMEngine(AnswerEngine):

    def __init__(self, api_key: str):
        # Models grouped by category, listed in decreasing order of preference
        models_config = {
            EngineType.NORMAL: ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-2-flash"],
            EngineType.SMALL: ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]             
        }

        self._model_pools = {}
        for engine_type, model_names in models_config.items():
            self._model_pools[engine_type] = {
                 # Prepare models
                "llms": [
                    ChatGoogleGenerativeAI(model=name, api_key=api_key, temperature=0.2, max_retries=1)
                    for name in model_names
                ],
                # Current model index
                "active_idx": 0 
            }

    # Invokes model according to pool and sticky fallback
    def _invoke_with_sticky_fallback(self, engine_type: EngineType, messages: list, tools: list | None = None) -> AIMessage:
        pool = self._model_pools.get(engine_type)

        llms = pool["llms"]
        current_idx = pool["active_idx"]
        num_models = len(llms)

        # Models will be tried in this order        
        order = [(current_idx + i) % num_models for i in range(num_models)]

        for idx in order:
            try:
                llm = llms[idx]
                if tools:
                    llm = llm.bind_tools(tools)
                
                response = llm.invoke(messages)

                # Model call succeeded, update active_idx
                pool["active_idx"] = idx
                return response

            except Exception as e:
                logger.warning(
                    f"{engine_type.value} engine: model at index {idx} ({llms[idx].model}) failed. Trying next one... Error: {e}"
                )

        raise RuntimeError(f"All available models for {engine_type.value} have failed.")

    # Entry point for the engine
    def invoke(self, engine_type: EngineType, agent_name: str, messages: list, tools: list | None = None) -> AIMessage:
        try:
            response = self._invoke_with_sticky_fallback(engine_type, messages, tools)
            logger.info("Agent %s: Tokens usage: %s. Response metadata: %s", agent_name, response.usage_metadata, response.response_metadata)
            return response
        except Exception as e:
            logger.error(f"Critical failure in pool '{engine_type.value}': {e}")
            return AIMessage(
                content="Lo siento, en este momento no puedo procesar tu solicitud debido a un problema técnico de conexión."
            )

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
