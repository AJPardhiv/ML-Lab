# gesture_controller.py
from __future__ import annotations
import time
from dataclasses import dataclass

import cv2
import numpy as np
import mediapipe as mp

from actions import Action, ActionBus

@dataclass
class GestureConfig:
    cam_index: int = 0
    max_hands: int = 1
    min_det_conf: float = 0.6
    min_track_conf: float = 0.6

    # Pinch detection (normalized distance threshold)
    pinch_thresh: float = 0.045

    # Smoothing for mouse movement
    smoothing: float = 0.35

class GestureController:
    def __init__(self, bus: ActionBus, cfg: GestureConfig = GestureConfig()) -> None:
        self.bus = bus
        self.cfg = cfg
        self.enabled = True

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=cfg.max_hands,
            min_detection_confidence=cfg.min_det_conf,
            min_tracking_confidence=cfg.min_track_conf,
        )

        self.prev_mouse = None
        self.dragging = False

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        # Release drag if disabling mid-drag
        if not enabled and self.dragging:
            self.bus.put(Action(type="MOUSE_UP"))
            self.dragging = False

    @staticmethod
    def _lm_xy(lm, w: int, h: int) -> tuple[int, int]:
        return int(lm.x * w), int(lm.y * h)

    @staticmethod
    def _norm_dist(a, b) -> float:
        return float(np.hypot(a.x - b.x, a.y - b.y))

    def _finger_up(self, lm, tip_id: int, pip_id: int) -> bool:
        # "Up" if tip is above PIP in image coords (y smaller)
        return lm[tip_id].y < lm[pip_id].y

    def run(self) -> None:
        cap = cv2.VideoCapture(self.cfg.cam_index)
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam.")

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue

                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = self.hands.process(rgb)

                if res.multi_hand_landmarks:
                    hand = res.multi_hand_landmarks[0]
                    lm = hand.landmark

                    # Landmarks used:
                    # thumb tip 4, index tip 8, middle tip 12
                    # index pip 6, middle pip 10
                    pinch = self._norm_dist(lm[4], lm[8]) < self.cfg.pinch_thresh
                    index_up = self._finger_up(lm, 8, 6)
                    middle_up = self._finger_up(lm, 12, 10)

                    # Open palm safety: index+middle up and pinch not active
                    open_palm_gesture = index_up and middle_up and not pinch

                    # Mouse move: when index finger up
                    if self.enabled and index_up and not middle_up:
                        ix, iy = self._lm_xy(lm[8], w, h)

                        # map camera coords -> screen-like coords (we send as relative intent)
                        # Here we just send raw and let executor map using pyautogui.size()
                        # Normalize to 0..1:
                        nx = ix / max(w, 1)
                        ny = iy / max(h, 1)

                        # smoothing in normalized space
                        if self.prev_mouse is None:
                            smx, smy = nx, ny
                        else:
                            smx = self.prev_mouse[0] * self.cfg.smoothing + nx * (1 - self.cfg.smoothing)
                            smy = self.prev_mouse[1] * self.cfg.smoothing + ny * (1 - self.cfg.smoothing)

                        self.prev_mouse = (smx, smy)
                        self.bus.put(Action(type="MOUSE_MOVE", x=int(smx * 10_000), y=int(smy * 10_000)))

                    # Drag/click via pinch
                    if self.enabled and pinch and index_up:
                        if not self.dragging:
                            self.bus.put(Action(type="MOUSE_DOWN"))
                            self.dragging = True
                    else:
                        if self.dragging:
                            self.bus.put(Action(type="MOUSE_UP"))
                            self.dragging = False

                    # Two-finger scroll mode (index+middle up)
                    if self.enabled and index_up and middle_up and not open_palm_gesture:
                        # crude scroll from middle fingertip vertical movement (delta)
                        mx, my = self._lm_xy(lm[12], w, h)
                        # use lm[0] wrist as a rough reference to stabilize
                        _, wy = self._lm_xy(lm[0], w, h)
                        dy = (wy - my) / max(h, 1)  # positive when fingers up
                        amount = int(np.clip(dy * 600, -600, 600))
                        if abs(amount) > 30:
                            self.bus.put(Action(type="SCROLL", amount=amount))

                # Display window (optional)
                cv2.imshow("Gesture Controller (press q)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.bus.put(Action(type="QUIT"))
                    break

                time.sleep(0.001)

        finally:
            cap.release()
            cv2.destroyAllWindows()