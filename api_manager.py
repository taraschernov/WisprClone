import os
import json
import requests
from groq import Groq
from config import (get_api_key, WHISPER_MODEL, LLM_MODEL, SYSTEM_PROMPT,
                    NOTION_CATEGORIZATION_PROMPT, get_notion_api_key,
                    get_notion_database_id, get_enable_notion,
                    get_notion_trigger_word)
import string
import re

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

    def refine_text(self, text, target_language=None):
        """Sends transcribed text to Groq LLM for refinement."""
        if not text.strip():
            return ""
            
        print(f"[API] Refining text... (Target Language: {target_language})")

        # Dynamic prompt construction
        prompt_instruction = SYSTEM_PROMPT
        if target_language and "Unknown" not in target_language:
            prompt_instruction += f"\nCRITICAL INSTRUCTION: The user's active keyboard layout is {target_language}. You MUST translate the transcription into {target_language} with perfect grammar. If it is already in {target_language}, just fix its grammar."

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": f"<transcription>\n{text}\n</transcription>"}
            ],
            model=LLM_MODEL,
            max_tokens=1024,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()

    def process_audio(self, audio_filepath, target_language=None):
        import time
        text_result = ""
        is_notion_note = False
        try:
            t1 = time.time()
            transcription = self.transcribe_audio(audio_filepath)
            t2 = time.time()
            print(f"[API] Transcription ({t2-t1:.2f}s): {transcription}")
            if not transcription.strip():
                return "", False
            
            t3 = time.time()
            refined = self.refine_text(transcription, target_language)
            t4 = time.time()
            print(f"[API] Refined ({t4-t3:.2f}s): {refined}")
            
            # --- Trigger Word Logic ---
            trigger_word = get_notion_trigger_word()
            enable_notion = get_enable_notion()
            
            if enable_notion and trigger_word:
                trigger_lower = trigger_word.lower()
                
                cleaned_transcription = transcription.lower().translate(str.maketrans('', '', string.punctuation))
                
                # Check if it was spoken in the raw transcription
                if trigger_lower in cleaned_transcription:
                    is_notion_note = True
                    
                    # Remove the trigger word at start or end of the *refined* text just in case the LLM left it in
                    pattern_start = re.compile(r'^[\s\W]*' + re.escape(trigger_word) + r'[\s\W]*', re.IGNORECASE)
                    pattern_end = re.compile(r'[\s\W]*' + re.escape(trigger_word) + r'[\s\W]*$', re.IGNORECASE)
                    
                    if pattern_start.search(refined):
                        refined = pattern_start.sub('', refined, count=1).strip()
                        if len(refined) > 0:
                            refined = refined[0].upper() + refined[1:]
                    elif pattern_end.search(refined):
                        refined = pattern_end.sub('', refined, count=1).strip()
                        if not refined.endswith(('.', '!', '?')) and len(refined) > 0:
                            refined += '.'
                else:
                    print(f"[Notion] Trigger word '{trigger_word}' not detected.")
            elif enable_notion:
                is_notion_note = True

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
        return text_result, is_notion_note

    def categorize_and_send_to_notion(self, text):
        if not get_enable_notion():
            return

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

