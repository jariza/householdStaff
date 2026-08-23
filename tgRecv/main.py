# Telegram interface module
# Presentation layer for interacting with the Telegram Bot API, handling the specific nuances of the Butler AI backend.

from dotenv import dotenv_values
import httpx
import json
import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Redact Telegram Bot API tokens in URLs
class TelegramTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        message = re.sub(r"(https://api\.telegram\.org/bot)[^/\s]+", r"\1***REDACTED***", message)
        record.msg = message
        record.args = ()
        return True

# Load and check configuration
config = dotenv_values(".env")

ALLOWED_USER_ID = int(config.get("ALLOWED_USER_ID"))
BUTLER_API_URL = config.get("BUTLER_API_URL")
LOG_LEVEL = config.get("LOG_LEVEL", "INFO").upper()
TOKEN = config.get("TELEGRAM_BOT_TOKEN")

if not ALLOWED_USER_ID or not BUTLER_API_URL or not TOKEN:
    raise RuntimeError("Missing variables in .env file: ALLOWED_USER_ID, BUTLER_API_URL or TELEGRAM_BOT_TOKEN")

# Load messages
with open("messages.json", "r", encoding="utf-8") as f:
    MESSAGES = json.load(f)

# Instantiate logger
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
for handler in logging.getLogger().handlers:
    telegram_token_filter = TelegramTokenFilter()
    handler.addFilter(telegram_token_filter)
logger = logging.getLogger(__name__)

# Sends text to Butler and receives the full answer (concatenated output from FastAPI SSE)
async def get_full_response_from_butler(user_input: str) -> str:
    accumulated_text = []

    # Increased timeout in case Butler takes long to answer
    timeout_config = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout_config) as client:
        async with client.stream("POST", BUTLER_API_URL, json={"user_input": user_input}) as response:
            
            response.raise_for_status()

            # Read SSE event line by line.
            # Events are expected to start with 'data:', ending mark is '[DONE]'
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_payload = line.removeprefix("data: ").strip()
                    if data_payload == "[DONE]":
                        break

                    try:
                        chunk_json = json.loads(data_payload)
                        if "content" in chunk_json:
                            accumulated_text.append(chunk_json["content"])
                    except json.JSONDecodeError:
                        # We are ignoring empty or invalid lines
                        continue

    return "".join(accumulated_text)

# Splits text in chunks (Telegram has a limit of 4096 chars per message)
def split_text(text: str, max_length: int = 4000) -> list[str]:
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# Bot start function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["welcome"])

# Bot answering function
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug("Telegram answer:\n{}".format(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)))

    if not update.message or not update.message.text:
        return
    user_text = update.message.text

    # Send "Writing..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Get answer from Butler and send it to Telegram
    try:
        full_response = await get_full_response_from_butler(user_text)
        if not full_response.strip():
            full_response = MESSAGES["no_content"]
        chunks = split_text(full_response)
        for chunk in chunks:
            await update.message.reply_text(chunk)
    except httpx.HTTPError as err:
        logger.error(f"Error while trying to connect to Butler: {err}")
        await update.message.reply_text(MESSAGES["http_error"])
    except Exception as e:
        logger.error(e)
        await update.message.reply_text(MESSAGES["unexpected"])

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    allowed_user_filter = filters.User(ALLOWED_USER_ID)
    
    app.add_handler(CommandHandler('start', start, filters=allowed_user_filter))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & allowed_user_filter, answer))
    app.run_polling()