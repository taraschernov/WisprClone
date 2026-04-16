import os
import json
import requests
from groq import Groq
from config import (get_api_key, WHISPER_MODEL, LLM_MODEL, 
                    NOTION_CATEGORIZATION_PROMPT, get_notion_api_key,
                    get_notion_database_id, get_enable_notion,
                    get_notion_trigger_word)
from config_manager import config_manager
import string
import re

class APIManager:
    def __init__(self):
        self.client = Groq(api_key=get_api_key())

    def transcribe_audio(self, audio_filepath):
        """Sends the audio file to Deepgram or fallback to Groq Whisper."""
        print("[API] Transcribing audio...")
        deepgram_api_key = config_manager.get("deepgram_api_key")
        dictation_lang = config_manager.get("dictation_language", "Russian")
        
        if deepgram_api_key:
            # Map dictation language to Deepgram language code
            lang_map = {
                "Russian": "ru",
                "English": "en",
                "English (UK)": "en",
                "Ukrainian": "uk",
                "German": "de",
                "French": "fr",
                "Spanish": "es",
            }
            lang_code = lang_map.get(dictation_lang, "ru")
            
            # Build Deepgram URL
            url = f"https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&punctuate=true&language={lang_code}"
            
            import requests
            with open(audio_filepath, "rb") as file:
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Token {deepgram_api_key}",
                        "Content-Type": "audio/wav"
                    },
                    data=file
                )
            try:
                data = response.json()
                transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
                return transcript
            except Exception as e:
                print(f"[API] Deepgram parsing error: {e}. Falling back to Groq...")

        # Fallback to Groq Whisper
        with open(audio_filepath, "rb") as file:
            transcription = self.client.audio.transcriptions.create(
                file=(os.path.basename(audio_filepath), file.read()),
                model=WHISPER_MODEL,
                response_format="text"
            )
        return str(transcription)

    def refine_text(self, text, target_language=None):
        """Sends transcribed text to Groq LLM for refinement/translation using presets."""
        if not text.strip():
            return ""
            
        from config import get_system_prompt, get_presets, get_current_mode, LLM_MODEL
        
        selected_mode = get_current_mode()
        print(f"[API] Refining text... (Mode: {selected_mode})")
        
        system_prompt = get_system_prompt()
        presets = get_presets()
        mode_instruction = presets.get(selected_mode, "")
        
        is_translate_on = config_manager.get("translate_to_layout", False)
        dictation_lang = config_manager.get("dictation_language", "Russian")
        
        # Add translation layer if triggered
        if is_translate_on and target_language and target_language != dictation_lang and "Unknown" not in target_language:
            mode_instruction += f"\n\nCRITICAL: You MUST also translate the entire text into {target_language} while maintaining the rules of the selected mode."

        full_system_content = f"{system_prompt}\n\n### Selected Mode: {selected_mode}\n{mode_instruction}"

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_system_content},
                {"role": "user", "content": f"<transcription>\n{text}\n</transcription>"}
            ],
            model=LLM_MODEL,
            max_tokens=2048,
            temperature=0.3
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
            
            # Skip LLM if translation is disabled — Deepgram already returns clean text
            # We ONLY run LLM if translation is requested OR it's a Notion note (to categorize)
            # Actually, let's logic: if translate_to_layout is ON and language is different -> Translate.
            
            is_translate_on = config_manager.get("translate_to_layout", False)
            dictation_lang = config_manager.get("dictation_language", "Russian")
            
            do_translate = is_translate_on and target_language and target_language != dictation_lang and "Unknown" not in target_language

            if do_translate:
                t3 = time.time()
                refined = self.refine_text(transcription, target_language)
                t4 = time.time()
                print(f"[API] Translated ({t4-t3:.2f}s) to {target_language}: {refined}")
            else:
                refined = transcription
                print(f"[API] Direct Mode (No translation).")
            
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

        topic = category_data.get("topic", "").strip() or "General"
        tags = [t for t in category_data.get("tags", []) if t and str(t).strip()]
        is_useful = category_data.get("is_useful", True)

        # Truncate title for Notion if too long
        title = text[:50] + "..." if len(text) > 50 else text

        payload = {
            "parent": {"database_id": notion_db_id},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Topic": {"select": {"name": topic}},
                "Tags": {"multi_select": [{"name": str(tag).strip()[:100]} for tag in tags[:3]]},
                "Useful": {"checkbox": bool(is_useful)},
                "Text": {"rich_text": [{"text": {"content": text[:2000]}}]}
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

