import cv2, mediapipe as mp, numpy as np, pickle, pyttsx3, time, os, threading, queue
from pathlib import Path

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh
mp_drawing_styles = mp.solutions.drawing_styles

# Load gesture model
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

def draw_hud(frame, face_center_x, face_center_y, gesture_label, confidence=0):
    """Draw Jarvis HUD around face center"""
    h, w = frame.shape[:2]
    
    # HUD circle radius based on face position
    radius = 150
    
    # Red/Cyan colors for HUD
    red = (0, 0, 255)
    cyan = (255, 255, 0)
    
    # Draw main circular HUD around head
    cv2.circle(frame, (face_center_x, face_center_y), radius, cyan, 3)
    cv2.circle(frame, (face_center_x, face_center_y), radius-10, red, 1)
    cv2.circle(frame, (face_center_x, face_center_y), radius+10, red, 1)
    
    # Draw crosshair in center
    cv2.line(frame, (face_center_x-30, face_center_y), (face_center_x+30, face_center_y), cyan, 2)
    cv2.line(frame, (face_center_x, face_center_y-30), (face_center_x, face_center_y+30), cyan, 2)
    
    # Draw corner squares
    corner_size = 40
    corners = [
        (face_center_x - radius - corner_size, face_center_y - radius - corner_size),
        (face_center_x + radius + corner_size, face_center_y - radius - corner_size),
        (face_center_x - radius - corner_size, face_center_y + radius + corner_size),
        (face_center_x + radius + corner_size, face_center_y + radius + corner_size),
    ]
    for corner in corners:
        cv2.rectangle(frame, (corner[0]-15, corner[1]-15), (corner[0]+15, corner[1]+15), red, 2)
    
    # Draw side panels
    panel_width = 80
    panel_height = 40
    
    # Left panel
    cv2.rectangle(frame, (face_center_x - radius - panel_width, face_center_y - panel_height//2),
                  (face_center_x - radius, face_center_y + panel_height//2), cyan, 2)
    cv2.putText(frame, 'STATUS', (face_center_x - radius - panel_width + 5, face_center_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, cyan, 1)
    
    # Right panel - show gesture
    cv2.rectangle(frame, (face_center_x + radius, face_center_y - panel_height//2),
                  (face_center_x + radius + panel_width, face_center_y + panel_height//2), cyan, 2)
    cv2.putText(frame, gesture_label[:8], (face_center_x + radius + 5, face_center_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, cyan, 1)
    
    # Top info panel
    cv2.rectangle(frame, (face_center_x - 100, face_center_y - radius - 40),
                  (face_center_x + 100, face_center_y - radius), cyan, 2)
    cv2.putText(frame, 'JARVIS ACTIVE', (face_center_x - 80, face_center_y - radius - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Bottom info panel with gesture details
    cv2.rectangle(frame, (face_center_x - 120, face_center_y + radius),
                  (face_center_x + 120, face_center_y + radius + 50), cyan, 2)
    cv2.putText(frame, f'Gesture: {gesture_label}', (face_center_x - 110, face_center_y + radius + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Draw scanning lines
    for i in range(0, radius*2, 20):
        offset = i - radius
        cv2.line(frame, (face_center_x - 5, face_center_y + offset), (face_center_x + 5, face_center_y + offset), red, 1)

cap = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as face_mesh, \
     mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6) as hands:
    
    last_gesture = ('', 0)
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        h, w = frame.shape[:2]
        img = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process face landmarks
        face_results = face_mesh.process(rgb)
        face_center_x, face_center_y = w // 2, h // 2
        
        if face_results.multi_face_landmarks:
            face_landmarks = face_results.multi_face_landmarks[0]
            # Use nose landmark as face center
            nose = face_landmarks.landmark[1]
            face_center_x = int(nose.x * w)
            face_center_y = int(nose.y * h)
        
        # Process hand gestures
        res = hands.process(rgb)
        gesture_label = 'STANDBY'
        
        if res.multi_hand_landmarks:
            lm = res.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(img, lm, mp_hands.HAND_CONNECTIONS)
            data = []
            for p in lm.landmark:
                data.extend([p.x, p.y])
            x = scaler.transform([data])
            pred = clf.predict(x)[0]
            gesture_label = pred
            now = time.time()
            
            # Announce gesture change
            if pred != last_gesture[0] or now - last_gesture[1] > 2.0:
                gesture_text = GESTURE_LABELS.get(pred, pred)
                voice_queue.put(gesture_text)
                last_gesture = (pred, now)
        
        # Draw HUD following head
        draw_hud(img, face_center_x, face_center_y, gesture_label)
        
        # Draw frame info
        cv2.putText(img, f'FPS: {int(cap.get(cv2.CAP_PROP_FPS))}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Jarvis AR HUD', img)
        
        if cv2.waitKey(1) & 0xFF == 27:
            print('Closing Jarvis AR HUD...')
            break

cap.release()
cv2.destroyAllWindows()
voice_queue.put(None)
print('✓ Jarvis AR HUD closed')
