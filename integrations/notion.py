import json
import requests
from groq import Groq
from config import (
    get_notion_api_key,
    get_notion_database_id,
    get_enable_notion,
    get_notion_trigger_word,
    NOTION_CATEGORIZATION_PROMPT,
    LLM_MODEL,
)
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger
from app_platform.notifications import notify
from i18n.translator import t as _t

logger = get_logger("yapclean.notion")


def categorize_and_send_to_notion(text: str) -> None:
    """Categorize text via LLM and send to Notion database."""
    if not get_enable_notion():
        return

    notion_api_key = get_notion_api_key()
    notion_db_id = get_notion_database_id()

    if not notion_api_key or not notion_db_id:
        logger.info("Notion integration not configured. Skipping.")
        return

    if not text.strip():
        return

    api_key = keyring_manager.get("api_key")
    if not api_key:
        logger.error("Groq API key not configured, cannot categorize for Notion.")
        return

    client = Groq(api_key=api_key)

    try:
        logger.info("Categorizing text for Notion...")
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": NOTION_CATEGORIZATION_PROMPT},
                {"role": "user", "content": f"<note>\n{text}\n</note>"},
            ],
            model=LLM_MODEL,
            temperature=0.1,
        )
        data_str = response.choices[0].message.content.strip()

        # Clean up potential markdown formatting from LLM
        if data_str.startswith("```json"):
            data_str = data_str[7:]
        if data_str.startswith("```"):
            data_str = data_str[3:]
        if data_str.endswith("```"):
            data_str = data_str[:-3]
        data_str = data_str.strip()

        category_data = json.loads(data_str)
    except Exception as e:
        logger.error(f"JSON parsing error or API error: {e}")
        category_data = {
            "is_useful": True,
            "topic": "Uncategorized",
            "tags": ["Voice Note"],
        }

    topic = category_data.get("topic", "").strip() or "General"
    tags = [t for t in category_data.get("tags", []) if t and str(t).strip()]
    is_useful = category_data.get("is_useful", True)

    title = text[:50] + "..." if len(text) > 50 else text

    payload = {
        "parent": {"database_id": notion_db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Topic": {"select": {"name": topic}},
            "Tags": {
                "multi_select": [
                    {"name": str(tag).strip()[:100]} for tag in tags[:3]
                ]
            },
            "Useful": {"checkbox": bool(is_useful)},
            "Text": {"rich_text": [{"text": {"content": text[:2000]}}]},
        },
    }

    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    try:
        logger.info("Sending to Notion database...")
        res = requests.post(
            "https://api.notion.com/v1/pages", json=payload, headers=headers
        )
        if res.status_code == 200:
            logger.info("Successfully added to Notion database.")
        else:
            logger.error(f"Error adding to Notion database: {res.text}")
    except Exception as e:
        logger.error(f"Notion request error: {e}")

