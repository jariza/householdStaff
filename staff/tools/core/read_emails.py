import email
import imaplib
import json
import logging
import ssl
from email.header import decode_header
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore

from tools import tool_config_load

logger = logging.getLogger(__name__)

# Build inbox search criteria
# sender: list of senders to search
def _build_inbox_search_criteria(sender: list[str]) -> str:
    if not sender:
        return ""
    if len(sender) == 1:
        return f'FROM "{sender[0]}"'
    criteria = f'FROM "{sender[-1]}"'
    for r in reversed(sender[:-1]):
        criteria = f'OR FROM "{r}" {criteria}'
    return criteria

# Decodes subject or names with special characters
def _decode_text(coded_text):
    if not coded_text:
        return ""
    parts = decode_header(coded_text)
    out_text = ""
    for content, codificacion in parts:
        if isinstance(content, bytes):
            out_text += content.decode(codificacion or 'utf-8', errors='ignore')
        else:
            out_text += str(content)
    return out_text

@tool
def read_emails(sender: list[str], config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    """
    Retrieves and permanently deletes emails from the inbox for specific senders.

    WARNING: This action has a destructive side effect. Once retrieved, the matching emails are immediately deleted from the mailbox so they are not processed twice. Do not call this tool repeatedly expecting to see the same emails again.

    Args: sender: Required list of sender email addresses to filter by (e.g., ["alice@example.com"]). Must always be a list, even for a single address.
    """

    user_id = config.get("configurable", {}).get("user_id")
    config = json.loads(tool_config_load(user_id, "read_emails", False, store))
    mail_pass = tool_config_load(user_id, "read_emails", True, store)

    if all(key in config for key in ["host", "user", "port"]):
        host = config["host"]
        user = config["user"]
        port = config["port"]
    else:
        logger.error("Wrong configuration format")
        return "ERROR: Wrong configuration format."

    try:
        with imaplib.IMAP4_SSL(host, port) as M:
            logger.debug("Reading emails from %s", sender)
            M.login(user, mail_pass)

            # Open INBOX
            status, _ = M.select()
            if status != "OK":
                return "ERROR: Unable to open INBOX."

            # Get emails
            status, data = M.search(None, _build_inbox_search_criteria(sender))
            if status != "OK":
                return "ERROR: Unable to search emails."

            mail_ids = data[0].split()
            if len(mail_ids) == 0:
                return "No emails found"

            out_text = ""
            for mail_id in mail_ids:
                # Extract email content
                res, msg_data = M.fetch(mail_id, '(RFC822)')
                if res != 'OK':
                    logger.info("Unable to open mail %s: %s", mail_id, res)
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        if msg.is_multipart():
                            body = ""
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

                out_text += f"Email received on {msg.get("Date")}\n"
                out_text += f"Subject: {_decode_text(msg.get("Subject"))}\n"
                out_text += f"{body}\nEND OF EMAIL\n"

                # Delete email
                M.store(mail_id, '+FLAGS', '\\Deleted')

            M.expunge()
            return out_text

    except (imaplib.IMAP4.error, ssl.SSLError, OSError) as e:
        return f"Exception reading email: {e}"

    finally:
        try:
            M.close()
            M.logout()
        except (imaplib.IMAP4.error, OSError):
            pass
