# main.py
from __future__ import annotations
import threading
import time
import webbrowser

import pyautogui

from actions import ActionBus, Action
from gesture_controller import GestureController
from voice_assistant import VoiceAssistant

pyautogui.FAILSAFE = True  # move mouse to top-left corner to stop PyAutoGUI

def executor_loop(bus: ActionBus, gesture: GestureController, voice: VoiceAssistant | None) -> None:
    screen_w, screen_h = pyautogui.size()
    mouse_is_down = False

    while True:
        action = bus.get()
        if action.type == "QUIT":
            break

        if action.type == "SAY" and action.text:
            if voice is not None:
                voice.say(action.text)

        elif action.type == "TOGGLE_GESTURES" and action.enabled is not None:
            gesture.set_enabled(action.enabled)

        elif action.type == "OPEN_URL" and action.url:
            webbrowser.open(action.url)

        elif action.type == "MOUSE_MOVE":
            # action.x/action.y are 0..10000 normalized ints
            if action.x is None or action.y is None:
                continue
            nx = max(0, min(10000, action.x)) / 10000.0
            ny = max(0, min(10000, action.y)) / 10000.0
            pyautogui.moveTo(int(nx * screen_w), int(ny * screen_h), _pause=False)

        elif action.type == "MOUSE_DOWN":
            if not mouse_is_down:
                pyautogui.mouseDown()
                mouse_is_down = True

        elif action.type == "MOUSE_UP":
            if mouse_is_down:
                pyautogui.mouseUp()
                mouse_is_down = False

        elif action.type == "CLICK":
            pyautogui.click()

        elif action.type == "DOUBLE_CLICK":
            pyautogui.doubleClick()

        elif action.type == "SCROLL" and action.amount is not None:
            pyautogui.scroll(int(action.amount))

        elif action.type == "TYPE_TEXT" and action.text:
            pyautogui.write(action.text, interval=0.01)

        time.sleep(0.001)

def main() -> None:
    bus = ActionBus()
    gesture = GestureController(bus)
    
    # Voice assistant is optional - gesture control will work without it
    try:
        voice = VoiceAssistant(bus)
    except Exception as e:
        print(f"[Main] Voice assistant initialization failed: {e}")
        print("[Main] Continuing with gesture control only")
        voice = None

    t_exec = threading.Thread(target=executor_loop, args=(bus, gesture, voice), daemon=True)
    t_gest = threading.Thread(target=gesture.run, daemon=True)
    
    t_exec.start()
    t_gest.start()
    
    # Only start voice thread if voice assistant is available
    if voice is not None:
        t_voice = threading.Thread(target=voice.run, daemon=True)
        t_voice.start()

    # Keep main thread alive until executor stops
    t_exec.join()

if __name__ == "__main__":
    main()