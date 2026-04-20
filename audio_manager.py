import numpy as np
import sounddevice as sd
import soundfile as sf
import tempfile
import os
from config import SAMPLE_RATE, CHANNELS, SILENCE_THRESHOLD_RMS, MIN_AUDIO_DURATION_SEC
from utils.logger import get_logger
from app_platform.notifications import notify
from i18n.translator import t

logger = get_logger("yapclean.audio")

class AudioManager:
    def __init__(self):
        self.recording = False
        self.stream = None
        self.audio_data = []

    def start_recording(self):
        """Starts capturing audio from the default microphone."""
        self.recording = True
        self.audio_data = []
        try:
            self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=self.callback)
            self.stream.start()
        except Exception as e:
            logger.error(f'Microphone access failed: {e}')
            notify('YapClean', t('error.mic_denied'), 'error')
            self.recording = False

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
        
        # FR-1.5: discard ONLY if BOTH conditions are true simultaneously
        # short meaningful words like "Ok", "Done", "Approved" must pass through
        duration = len(audio_concat) / SAMPLE_RATE
        rms = np.sqrt(np.mean(np.square(audio_concat)))
        if duration < MIN_AUDIO_DURATION_SEC and rms < SILENCE_THRESHOLD_RMS:
            logger.info(f"Audio discarded: too short ({duration:.2f}s) AND silent (RMS={rms:.4f})")
            return None
            
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        
        sf.write(temp_file_path, audio_concat, SAMPLE_RATE)
        logger.info(f"Saved to {temp_file_path}")
        return temp_file_path


