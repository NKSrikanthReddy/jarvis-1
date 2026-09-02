"""Voice and Text-to-Speech (TTS) module for JARVIS spoken announcements."""

import shutil
import subprocess
import threading
from typing import Optional

from config import Config
from modules.base import BaseModule
from utils.logger import print_status, print_warning


class VoiceModule(BaseModule):
    """Voice output module for JARVIS.
    
    Supports native macOS 'say' command with British accent voices (e.g. Daniel / Oliver)
    or pyttsx3 fallback.
    """

    def __init__(self, voice_name: Optional[str] = "Daniel", rate: int = Config.VOICE_RATE):
        super().__init__(name="VoiceModule", description="Spoken voice synthesizer for JARVIS announcements")
        self.voice_name = voice_name
        self.rate = rate
        self.engine_type = None

    def initialize(self) -> bool:
        """Check for available TTS engines."""
        # On macOS, check if 'say' command exists
        if shutil.which("say"):
            self.engine_type = "macos_say"
            self.is_initialized = True
            return True

        # Fallback to pyttsx3 if installed
        try:
            import pyttsx3
            self.engine_type = "pyttsx3"
            self.is_initialized = True
            return True
        except ImportError:
            pass

        print_warning("No TTS engine available (macOS 'say' or pyttsx3). Voice module disabled.")
        self.is_initialized = False
        return False

    def execute(self, text: str, blocking: bool = False) -> bool:
        """Speak the provided text."""
        if not self.is_initialized:
            if not self.initialize():
                return False

        # Clean text for speech (remove markdown asterisks, hashes, urls)
        speech_text = self._clean_for_speech(text)
        if not speech_text:
            return False

        if blocking:
            self._speak(speech_text)
        else:
            threading.Thread(target=self._speak, args=(speech_text,), daemon=True).start()
        return True

    def _speak(self, text: str) -> None:
        """Internal speech dispatcher."""
        try:
            if self.engine_type == "macos_say":
                # Use macOS say command with Daniel (British voice) if available
                cmd = ["say", "-r", str(self.rate)]
                if self.voice_name:
                    cmd.extend(["-v", self.voice_name])
                cmd.append(text)
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    # Fallback to default voice if named voice isn't installed
                    subprocess.run(["say", "-r", str(self.rate), text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif self.engine_type == "pyttsx3":
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self.rate)
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            print_warning(f"Voice output encountered an error: {e}")

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Strip markdown markers and technical artifacts for natural speech."""
        import re
        # Remove markdown links, headings, bold, bullet points
        text = re.sub(r"#+\s*", "", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"`[^`]*`", "", text)
        text = re.sub(r"[-*]\s+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Truncate speech text if excessively long
        if len(text) > 1000:
            text = text[:1000] + "... and several other items, sir."
        return text
