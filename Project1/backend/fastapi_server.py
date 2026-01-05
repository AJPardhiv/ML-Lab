import cv2, mediapipe as mp, asyncio, json, pickle, numpy as np, time, os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
app = FastAPI()
mp_hands = mp.solutions.hands; mp_drawing = mp.solutions.drawing_utils
# Load model with proper path handling
model_path = Path(__file__).parent.parent / 'models' / 'gesture_rf.pkl'
if not model_path.exists():
    print(f"ERROR: Model not found at {model_path}. Please train model first: python scripts/train_model.py")
    clf = None; scaler = None
else:
    mod = pickle.load(open(model_path,'rb')); clf = mod['model']; scaler = mod['scaler']
GESTURE_ACTIONS = {'open_palm':'activate','fist':'close_app','thumbs_up':'confirm','swipe_right':'next','swipe_left':'prev','two_fingers':'volume_toggle','pointing':'mouse_control'}
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def send(self, msg):
        for c in self.active_connections:
            await c.send_text(json.dumps(msg))
manager = ConnectionManager()
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    if clf is None or scaler is None:
        await websocket.accept()
        await websocket.send_json({'error': 'Model not trained. Run: python scripts/train_model.py'})
        await websocket.close()
        return
    await manager.connect(websocket)
    try:
        cap = cv2.VideoCapture(0)
        with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6) as hands:
            while True:
                data = await websocket.receive_text()
                # Non-blocking: process frames and send updates
                ret, frame = cap.read()
                if not ret: break
                img = cv2.flip(frame,1); rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                res = hands.process(rgb)
                if res.multi_hand_landmarks:
                    lm = res.multi_hand_landmarks[0]
                    landmarks = [{'x':p.x,'y':p.y} for p in lm.landmark]
                    # predict
                    arr = np.array([val for p in landmarks for val in (p['x'], p['y'])]).reshape(1,-1)
                    arr = scaler.transform(arr); pred = clf.predict(arr)[0]
                    action = GESTURE_ACTIONS.get(pred,'none')
                    await manager.send({'type':'landmarks','landmarks':landmarks})
                    await manager.send({'type':'gesture','gesture':pred,'action':action})
                else:
                    await manager.send({'type':'status','status':'no_hand'})
                await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print('Error:', e)
