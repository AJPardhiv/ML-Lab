# actions.py
from __future__ import annotations
from dataclasses import dataclass
from queue import Queue
from typing import Optional, Literal

ActionType = Literal[
    "MOUSE_MOVE",
    "MOUSE_DOWN",
    "MOUSE_UP",
    "CLICK",
    "DOUBLE_CLICK",
    "SCROLL",
    "TYPE_TEXT",
    "TOGGLE_GESTURES",
    "SAY",
    "OPEN_URL",
    "QUIT",
]

@dataclass
class Action:
    type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    amount: Optional[int] = None
    text: Optional[str] = None
    enabled: Optional[bool] = None
    url: Optional[str] = None

class ActionBus:
    def __init__(self) -> None:
        self.q: Queue[Action] = Queue()

    def put(self, action: Action) -> None:
        self.q.put(action)

    def get(self, timeout: Optional[float] = None) -> Action:
        return self.q.get(timeout=timeout)
    