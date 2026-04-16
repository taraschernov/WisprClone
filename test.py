import os
import wave
import numpy as np
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

filename = "test_audio.wav"
sample_rate = 16000
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

with wave.open(filename, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_data.tobytes())

print(f"API Key starting with: {GROQ_API_KEY[:5]}...")

client = Groq(api_key=GROQ_API_KEY)
try:
    with open(filename, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(filename, file.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    print("Transcription success:", transcription)
except Exception as e:
    import traceback
    traceback.print_exc()

if os.path.exists(filename):
    os.remove(filename)
