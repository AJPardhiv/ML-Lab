# voice_assistant.py
from __future__ import annotations
import json
import queue
import re
import time
import webbrowser
from dataclasses import dataclass

import pyttsx3
import sounddevice as sd
from vosk import Model, KaldiRecognizer

from actions import Action, ActionBus

@dataclass
class VoiceConfig:
    model_path: str = "models/vosk-model-small-en-us-0.15"
    samplerate: int = 16000
    device: int | None = None  # set if you have multiple mics

class VoiceAssistant:
    def __init__(self, bus: ActionBus, cfg: VoiceConfig = VoiceConfig()) -> None:
        self.bus = bus
        self.cfg = cfg
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 175)

        # Try to load Vosk model, but continue without it if not available
        self.model = None
        self.rec = None
        try:
            self.model = Model(cfg.model_path)
            self.rec = KaldiRecognizer(self.model, cfg.samplerate)
            self.rec.SetWords(False)
            print("[VoiceAssistant] Vosk model loaded successfully")
        except Exception as e:
            print(f"[VoiceAssistant] Warning: Vosk model not available ({e})")
            print("[VoiceAssistant] Voice commands disabled. Gesture control only.")

        self._audio_q: "queue.Queue[bytes]" = queue.Queue()

    def say(self, text: str) -> None:
        self.tts.say(text)
        self.tts.runAndWait()

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            # ignore status spam; could log if desired
            pass
        self._audio_q.put(bytes(indata))

    def _handle_text(self, text: str) -> None:
        t = text.strip().lower()
        if not t:
            return

        # Quit
        if t in {"quit", "exit", "stop program", "close program"}:
            self.bus.put(Action(type="SAY", text="Quitting."))
            self.bus.put(Action(type="QUIT"))
            return

        # Toggle gestures
        if "stop gestures" in t or "disable gestures" in t:
            self.bus.put(Action(type="TOGGLE_GESTURES", enabled=False))
            self.bus.put(Action(type="SAY", text="Gestures disabled."))
            return

        if "start gestures" in t or "enable gestures" in t:
            self.bus.put(Action(type="TOGGLE_GESTURES", enabled=True))
            self.bus.put(Action(type="SAY", text="Gestures enabled."))
            return

        # Mouse actions
        if t in {"click", "mouse click"}:
            self.bus.put(Action(type="CLICK"))
            return

        if "double click" in t:
            self.bus.put(Action(type="DOUBLE_CLICK"))
            return

        if "scroll up" in t:
            self.bus.put(Action(type="SCROLL", amount=400))
            return

        if "scroll down" in t:
            self.bus.put(Action(type="SCROLL", amount=-400))
            return

        # Type command: "type hello world"
        m = re.match(r"^(type|write)\s+(.*)$", t)
        if m:
            self.bus.put(Action(type="TYPE_TEXT", text=m.group(2)))
            return

        # Open sites
        if "open youtube" in t:
            self.bus.put(Action(type="OPEN_URL", url="https://www.youtube.com"))
            return

        if "open google" in t:
            self.bus.put(Action(type="OPEN_URL", url="https://www.google.com"))
            return

        if "time" in t:
            now = time.strftime("%I:%M %p")
            self.bus.put(Action(type="SAY", text=f"It is {now}."))
            return

        # Default response
        self.bus.put(Action(type="SAY", text="Sorry, I did not understand that command."))

    def run(self) -> None:
        if self.model is None or self.rec is None:
            print("[VoiceAssistant] Voice recognition not available, voice thread exiting")
            return
        
        self.bus.put(Action(type="SAY", text="Voice assistant started."))

        with sd.RawInputStream(
            samplerate=self.cfg.samplerate,
            blocksize=8000,
            device=self.cfg.device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        ):
            while True:
                data = self._audio_q.get()
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "")
                    self._handle_text(text)
                else:
                    # partial = json.loads(self.rec.PartialResult()).get("partial","")
                    pass