# Jarvis Hand-Gesture + Voice — Full ML Project

This repo contains a complete scaffold for a Jarvis-style assistant controlled by hand gestures and voice.

**Included:**
- data collection script (MediaPipe landmarks)
- training script (RandomForest)
- real-time assistant (gesture detection + TTS)
- FastAPI backend (WebSocket streaming to frontend)
- React HUD component (frontend/JarvisHUD.jsx)
- requirements.txt

**How to use (quick):**
1. Install Python deps: `pip install -r requirements.txt`
2. Collect gesture data: `python scripts/collect_data.py --label open_palm --samples 300`
3. Train model: `python scripts/train_model.py`
4. Run backend: `uvicorn backend.fastapi_server:app --port 8000 --reload`
5. Run React app and include `frontend/JarvisHUD.jsx` (or use provided minimal frontend)

See scripts/ and backend/ for details.
