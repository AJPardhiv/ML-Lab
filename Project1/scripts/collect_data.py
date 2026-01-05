import cv2, mediapipe as mp, numpy as np, pandas as pd, argparse, os
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
parser.add_argument('--samples', type=int, default=300)
parser.add_argument('--output', default='data/landmarks')
args = parser.parse_args()
os.makedirs(args.output, exist_ok=True)
outfile = os.path.join(args.output, f'{args.label}.csv')
print(f'Collecting {args.samples} samples for gesture: {args.label}')
print('Position your hand in front of the camera. Press ESC to cancel.')
cap = cv2.VideoCapture(0)
with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6) as hands:
    rows=[]; collected=0
    while collected < args.samples:
        ret, frame = cap.read()
        if not ret: break
        img = cv2.flip(frame,1); rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb)
        h,w,_ = img.shape
        if res.multi_hand_landmarks:
            lm = res.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(img, lm, mp_hands.HAND_CONNECTIONS)
            data=[]
            for p in lm.landmark:
                data.extend([p.x, p.y])
            rows.append(data + [args.label])
            collected += 1
            cv2.putText(img, f'Collected: {collected}/{args.samples}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0),2)
        else:
            cv2.putText(img, 'No hand detected', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)
        cv2.imshow('Collect Data', img)
        if cv2.waitKey(1) & 0xFF == 27: 
            print('Cancelled by user')
            break
cap.release(); cv2.destroyAllWindows()
if collected == 0:
    print('No samples collected!')
    exit(1)
import pandas as pd
cols = [f'x{i}' if i%2==0 else f'y{i}' for i in range(42)]; cols.append('label')
df = pd.DataFrame(rows, columns=cols); df.to_csv(outfile, index=False)
print(f'✓ Saved {outfile} with {len(df)} samples')
