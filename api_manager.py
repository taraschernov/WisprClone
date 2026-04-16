import os
import json
import requests
from groq import Groq
from config import get_api_key, WHISPER_MODEL, LLM_MODEL, SYSTEM_PROMPT, NOTION_CATEGORIZATION_PROMPT, get_notion_api_key, get_notion_database_id

class APIManager:
    def __init__(self):
        self.client = Groq(api_key=get_api_key())

    def transcribe_audio(self, audio_filepath):
        """Sends the audio file to Groq Whisper model."""
        print("[API] Transcribing audio...")
        with open(audio_filepath, "rb") as file:
            transcription = self.client.audio.transcriptions.create(
                file=(os.path.basename(audio_filepath), file.read()),
                model=WHISPER_MODEL,
                response_format="text"
            )
        # return as string
        return str(transcription)

    def refine_text(self, text):
        """Sends transcribed text to Groq LLM for refinement."""
        if not text.strip():
            return ""
            
        print("[API] Refining text...")
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"<transcription>\n{text}\n</transcription>"}
            ],
            model=LLM_MODEL,
            max_tokens=1024,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()

    def process_audio(self, audio_filepath):
        text_result = ""
        try:
            transcription = self.transcribe_audio(audio_filepath)
            print(f"[API] Transcription: {transcription}")
            if not transcription.strip():
                return ""
            
            refined = self.refine_text(transcription)
            print(f"[API] Refined: {refined}")
            text_result = refined
        except Exception as e:
            print(f"[API] Error: {e}")
            text_result = ""
        finally:
            if os.path.exists(audio_filepath):
                try:
                    os.remove(audio_filepath)
                except Exception as cleanup_error:
                    print(f"[API] Failed to delete temp file: {cleanup_error}")
        return text_result

    def categorize_and_send_to_notion(self, text):
        notion_api_key = get_notion_api_key()
        notion_db_id = get_notion_database_id()

        if not notion_api_key or not notion_db_id:
            print("[Notion] Integration not configured. Skipping.")
            return

        if not text.strip():
            return

        try:
            print("[Notion] Categorizing text...")
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": NOTION_CATEGORIZATION_PROMPT},
                    {"role": "user", "content": f"<note>\n{text}\n</note>"}
                ],
                model=LLM_MODEL,
                temperature=0.1
            )
            data_str = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting from LLM
            if data_str.startswith("```json"): data_str = data_str[7:]
            if data_str.startswith("```"): data_str = data_str[3:]
            if data_str.endswith("```"): data_str = data_str[:-3]
            data_str = data_str.strip()
            
            category_data = json.loads(data_str)
        except Exception as e:
            print(f"[Notion] JSON parsing error or API error: {e}")
            # Fallback data if JSON fails
            category_data = {
                "is_useful": True,
                "topic": "Uncategorized",
                "tags": ["Voice Note"]
            }

        topic = category_data.get("topic", "Uncategorized")
        tags = category_data.get("tags", [])
        is_useful = category_data.get("is_useful", True)

        # Truncate title for Notion if too long
        title = text[:50] + "..." if len(text) > 50 else text

        payload = {
            "parent": {"database_id": notion_db_id},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Topic": {"select": {"name": topic}},
                "Tags": {"multi_select": [{"name": tag} for tag in tags[:3]]},
                "Useful": {"checkbox": is_useful},
                "Text": {"rich_text": [{"text": {"content": text}}]}
            }
        }

        headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        try:
            print("[Notion] Sending to database...")
            res = requests.post("https://api.notion.com/v1/pages", json=payload, headers=headers)
            if res.status_code == 200:
                print("[Notion] Successfully added to Notion database.")
            else:
                print(f"[Notion] Error adding to database: {res.text}")
        except Exception as e:
            print(f"[Notion] Request error: {e}")

