import cv2, mediapipe as mp, numpy as np, pickle, pyttsx3, time, os, threading, queue
from pathlib import Path
mp_hands = mp.solutions.hands; mp_drawing = mp.solutions.drawing_utils
# Load model with proper path handling
model_path = Path(__file__).parent.parent / 'models' / 'gesture_rf.pkl'
if not model_path.exists():
    print(f"ERROR: Model not found at {model_path}. Please train model first: python scripts/train_model.py")
    exit(1)
mod = pickle.load(open(model_path,'rb')); clf = mod['model']; scaler = mod['scaler']

# Initialize audio engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)
voice_queue = queue.Queue()

def voice_worker():
    """Background thread for speaking"""
    while True:
        try:
            text = voice_queue.get(timeout=1)
            if text is None:
                break
            print(f'🎤 Speaking: {text}')
            engine.say(text)
            engine.runAndWait()
        except queue.Empty:
            continue

# Start voice thread
voice_thread = threading.Thread(target=voice_worker, daemon=True)
voice_thread.start()

GESTURE_ACTIONS = {'open_palm':'activate','fist':'close_app','thumbs_up':'confirm','swipe_right':'next','swipe_left':'prev','two_fingers':'volume_toggle','pointing':'mouse_control'}
GESTURE_LABELS = {
    'open_palm': 'Open Palm detected',
    'fist': 'Fist detected',
    'thumbs_up': 'Thumbs Up detected',
    'swipe_right': 'Swipe Right detected',
    'swipe_left': 'Swipe Left detected',
    'two_fingers': 'Two Fingers detected',
    'pointing': 'Pointing detected'
}
cap = cv2.VideoCapture(0)
with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6) as hands:
    last_gesture = ('', 0); 
    while True:
        ret, frame = cap.read()
        if not ret: break
        img = cv2.flip(frame,1); rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb); label=''
        if res.multi_hand_landmarks:
            lm = res.multi_hand_landmarks[0]; mp_drawing.draw_landmarks(img, lm, mp_hands.HAND_CONNECTIONS)
            data = []; 
            for p in lm.landmark: data.extend([p.x, p.y])
            x = scaler.transform([data]); pred = clf.predict(x)[0]; label = pred
            now = time.time()
            # Announce gesture change (debounce with 2 second delay)
            if pred != last_gesture[0] or now - last_gesture[1] > 2.0:
                gesture_text = GESTURE_LABELS.get(pred, pred)
                action = GESTURE_ACTIONS.get(pred, 'unknown')
                print(f'✓ Detected: {gesture_text}'); 
                # Queue speech (non-blocking)
                voice_queue.put(gesture_text)
                last_gesture = (pred, now)
                with open('last_state.txt','w') as f: f.write(f'{pred}|{action}')
        # Display gesture label on screen
        cv2.putText(img, f'Gesture: {label}', (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)
        cv2.imshow('Jarvis - Gesture Recognition', img)
        if cv2.waitKey(1) & 0xFF == 27: 
            print('Closing Jarvis...')
            break
cap.release(); cv2.destroyAllWindows()
voice_queue.put(None)  # Signal voice thread to stop
print('✓ Jarvis closed')
