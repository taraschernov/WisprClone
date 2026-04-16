import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import os
from config import SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD_RMS, MIN_AUDIO_DURATION_SEC

class AudioManager:
    def __init__(self):
        self.recording = False
        self.stream = None
        self.audio_data = []

    def start_recording(self):
        """Starts capturing audio from the default microphone."""
        self.recording = True
        self.audio_data = []
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=self.callback)
        self.stream.start()

    def callback(self, indata, frames, time, status):
        """Callback for sounddevice stream."""
        if self.recording:
            self.audio_data.append(indata.copy())

    def stop_recording(self):
        """Stops capturing and returns path to temp WAV file, or None if silent/too short."""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        if not self.audio_data:
            return None
            
        # Concatenate array
        audio_concat = np.concatenate(self.audio_data, axis=0)
        
        # Calculate duration
        duration = len(audio_concat) / SAMPLE_RATE
        if duration < MIN_AUDIO_DURATION_SEC:
            print("[Audio] Audio too short, ignoring.")
            return None
            
        # Check for silence (RMS)
        rms = np.sqrt(np.mean(np.square(audio_concat)))
        if rms < SILENCE_THRESHOLD_RMS:
            print(f"[Audio] Audio silent (RMS={rms:.4f} < {SILENCE_THRESHOLD_RMS}), ignoring.")
            return None
            
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close() # Close to allow sf.write to open it
        
        sf.write(temp_file_path, audio_concat, SAMPLE_RATE)
        print(f"[Audio] Saved to {temp_file_path}")
        return temp_file_path
