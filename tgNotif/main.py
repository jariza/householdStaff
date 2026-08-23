# Telegram notification service
# Asynchronous service  that exposes an HTTP endpoint to send messages to a specific Telegram chat via the Telegram Bot API.

from contextlib import asynccontextmanager
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
import httpx
import logging
from pydantic import BaseModel

# Load and check configuration
config = dotenv_values(".env")

DESTINATION_CHAT_ID = config.get("DESTINATION_CHAT_ID")
LOG_LEVEL = config.get("LOG_LEVEL", "INFO").upper()
TOKEN = config.get("TELEGRAM_BOT_TOKEN")

if not DESTINATION_CHAT_ID or not TOKEN:
    raise RuntimeError("Missing variables in .env file: DESTINATION_CHAT_ID or TELEGRAM_BOT_TOKEN")

# Instantiate logger
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# Create HTTP client in lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{TOKEN}", timeout=10.0) as client:
        app.state.http_client = client
        yield

# Instantiate FastAPI app
app = FastAPI(title="Telegram notifications service", lifespan=lifespan)

# Define payload structure for requests
class NotificationRequest(BaseModel):
    message: str

# Request process
@app.post("/notify")
async def send_notification(payload: NotificationRequest, request: Request):
    client = request.app.state.http_client
    try:
        response = await client.post("/sendMessage", json={
            "CHAT_ID": DESTINATION_CHAT_ID,
            "text": payload.message,
        })
        res_json = response.json()

        if not res_json.get("ok"):
            desc = res_json.get("description", "Unknown error")
            logger.error(f"Telegram error: {desc}")
            raise HTTPException(status_code=502, detail=f"Message rejected by Telegram: {desc}")

        logger.info("Notification delivered to Telegram")
        return {"status": "success"}

    except httpx.RequestError as e:
        logger.error(f"Telegram network error: {e}")
        raise HTTPException(status_code=503, detail="Cannot connect to Telegram API")