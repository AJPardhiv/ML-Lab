import glob, pandas as pd, numpy as np, pickle, os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
files = glob.glob('data/landmarks/*.csv')
if not files:
    print('ERROR: No landmark CSVs found in data/landmarks.')
    print('SOLUTION: Collect data first using:')
    print('  python scripts/collect_data.py --label open_palm --samples 300')
    print('  python scripts/collect_data.py --label fist --samples 300')
    print('  python scripts/collect_data.py --label thumbs_up --samples 300')
    print('  (repeat for all gestures)')
    raise SystemExit
print(f'Found {len(files)} gesture files: {files}')
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
print(f'Total samples: {len(df)}')
print(f'Classes: {df["label"].unique()}')
labels = df['label']; X = df.drop(columns=['label']).values
scaler = StandardScaler(); Xs = scaler.fit_transform(X)
X_train,X_test,y_train,y_test = train_test_split(Xs, labels, test_size=0.2, stratify=labels, random_state=42)
clf = RandomForestClassifier(n_estimators=200, random_state=42); clf.fit(X_train,y_train)
pred = clf.predict(X_test); 
print('\n=== Classification Report ===')
print(classification_report(y_test,pred))
os.makedirs('models', exist_ok=True)
with open('models/gesture_rf.pkl','wb') as f: pickle.dump({'model':clf,'scaler':scaler}, f)
print('✓ Saved models/gesture_rf.pkl')
