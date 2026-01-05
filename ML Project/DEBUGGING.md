# DEBUGGING.md - Troubleshooting Guide

This guide helps diagnose and fix common issues with the Gesture-Based Laptop Controller.

## 🔍 Diagnostic Checklist

Run this first:
```bash
python setup_check.py
```

This will verify:
- ✓ Python version
- ✓ All dependencies installed
- ✓ Webcam working
- ✓ Microphone available
- ✓ Vosk model present
- ✓ OS permissions

---

## 🐛 Common Issues & Fixes

### 1. **Webcam Issues**

#### Error: "Cannot open webcam" or "Cannot find camera"

**Root Cause**: Camera not connected, in use, or wrong driver

**Fix Priority Order**:

1. **Check if camera is in use**
   ```bash
   # Close these apps: Zoom, Skype, Discord, WebEx, other video apps
   # Kill the Python process using camera
   ```

2. **Test camera directly**
   ```python
   import cv2
   cap = cv2.VideoCapture(0)
   print(cap.isOpened())  # Should print True
   ```

3. **Try different camera index**
   ```python
   # If 0 doesn't work, try 1, 2, etc.
   cap = cv2.VideoCapture(1)
   cap = cv2.VideoCapture(2)
   ```

4. **Check Windows Device Manager**
   - Right-click Start menu → Device Manager
   - Expand "Cameras"
   - If camera shows ⚠️, update driver from manufacturer website

5. **Reinstall OpenCV**
   ```bash
   pip uninstall opencv-python
   pip install opencv-python==4.8.1.78
   ```

**If still failing**: Camera hardware may be defective. Try USB camera.

---

#### Error: Webcam opens but shows black/blurry image

**Root Cause**: Poor lighting, dirty lens, or autofocus issues

**Fix Priority Order**:

1. **Check lighting**
   - Ensure bright, even lighting
   - Avoid backlighting (light behind hand)
   - Natural window light works well

2. **Clean lens**
   - Wipe camera lens with soft cloth
   - Remove any protective stickers

3. **Adjust camera settings**
   ```python
   # In gesture_controller.py after creating capture:
   cap.set(cv2.CAP_PROP_BRIGHTNESS, 100)
   cap.set(cv2.CAP_PROP_CONTRAST, 50)
   cap.set(cv2.CAP_PROP_SATURATION, 100)
   cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
   ```

4. **Adjust resolution**
   ```python
   # Try lower resolution for faster autofocus
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```

---

### 2. **Gesture Not Recognized**

#### Gestures not being detected or detected incorrectly

**Root Cause**: Hand tracking failed, poor lighting, or hand out of frame

**Fix Priority Order**:

1. **Check hand visibility**
   - Position hand fully in frame
   - Move closer to camera (6-12 inches)
   - Ensure good lighting on hand

2. **Verify MediaPipe detection**
   - Hand landmarks should show in window
   - If no landmarks appear, lighting is likely the issue

3. **Increase detection sensitivity**
   - Edit `gesture_controller.py` line ~50:
   ```python
   "min_detection_confidence": 0.5,      # Lower = more sensitive
   "min_tracking_confidence": 0.3,       # Lower = more sensitive
   ```

4. **Adjust gesture thresholds**
   - Edit `gesture_controller.py` line ~52:
   ```python
   PINCH_THRESHOLD = 0.03  # Lower = easier to pinch
   PALM_THRESHOLD = 0.08   # Lower = stricter palm detection
   ```

5. **Enable debug output**
   - Edit `gesture_controller.py` line ~400:
   ```python
   print(f"[DEBUG] Index-thumb distance: {distance}")
   ```

6. **Check gesture cooldown**
   - Edit `gesture_controller.py` line ~63:
   ```python
   self.gesture_cooldown = 0.2  # Reduce if gestures feel sluggish
   ```

---

#### Specific gesture not working

**For CLICK (pinch)**:
- Gesture: Thumb and index finger very close together
- Issue: Fingers not touching enough
- Fix: Lower `PINCH_THRESHOLD` in config

**For SCROLL**:
- Gesture: Index and middle finger close together
- Issue: Fingers not together enough
- Fix: Lower threshold (see above)

**For PAUSE** (open palm):
- Gesture: All fingers fully extended and spread apart
- Issue: Fingers not spread enough
- Fix: Check lighting, move hand closer

**For MOVE** (index finger tracking):
- Should always work if hand detected
- If not working: Hand not in frame or not detected

---

### 3. **Voice Assistant Issues**

#### Error: "Vosk model not found"

**Root Cause**: Model file not downloaded or in wrong location

**Fix Priority Order**:

1. **Verify model directory structure**
   ```
   project_root/
   ├── model/
   │   ├── conf/
   │   │   └── model.conf       # This file must exist
   │   ├── acoustic_model
   │   ├── am/
   │   └── ...
   ```

2. **Download Vosk model**
   
   **Windows (PowerShell)**:
   ```powershell
   $url = 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip'
   Invoke-WebRequest $url -O vosk-model.zip
   Expand-Archive vosk-model.zip -DestinationPath .
   Rename-Item vosk-model-en-us-0.42-gigaspeech model
   Remove-Item vosk-model.zip
   ```
   
   **macOS/Linux**:
   ```bash
   wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip
   unzip vosk-model.zip
   mv vosk-model-en-us-0.42-gigaspeech model
   rm vosk-model.zip
   ```

3. **Verify extraction**
   ```bash
   ls model/conf/model.conf  # Should exist
   ```

4. **If all else fails**: Disable voice assistant, use gesture control only

---

#### Error: Microphone not detected or voice recognition not working

**Root Cause**: Microphone not configured, or PyAudio issue

**Fix Priority Order**:

1. **Test microphone directly**
   ```bash
   # Windows (PowerShell):
   python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count())"
   # Should print > 0
   ```

2. **Check OS permissions**
   
   **Windows**:
   - Settings → Privacy & Security → Microphone
   - Ensure app can access microphone
   
   **macOS**:
   - System Preferences → Security & Privacy → Microphone
   - Grant Terminal/Python access
   
   **Linux**:
   ```bash
   # Check if in audio group
   groups $USER
   # If not, add:
   sudo usermod -a -G audio $USER
   # Logout and login
   ```

3. **Install PyAudio**
   ```bash
   pip uninstall pyaudio
   pip install pyaudio
   ```
   
   **If fails on Windows**: Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

4. **Test voice recognition**
   ```python
   from voice_assistant import VoskSTTEngine
   stt = VoskSTTEngine()
   text = stt.recognize_from_mic(duration_seconds=3)
   print(text)
   ```

5. **Check microphone volume**
   - Ensure microphone isn't muted in OS
   - Check volume level in OS sound settings

---

#### Voice commands not recognized

**Root Cause**: Speech not clear, background noise, or accent

**Fix Priority Order**:

1. **Speak clearly**
   - Enunciate each word
   - Speak at normal volume and pace
   - Face microphone

2. **Reduce background noise**
   - Close doors/windows
   - Turn off fans, AC, speakers
   - Disconnect other microphones

3. **Check command matching**
   - Edit `voice_assistant.py` line ~200:
   ```python
   "fuzzy_match_threshold": 0.7  # Lower = more lenient
   ```

4. **Test with recording**
   ```python
   # Save audio to file for debugging
   import sounddevice as sd
   import soundfile as sf
   duration = 5
   audio = sd.rec(int(16000 * duration), samplerate=16000, channels=1)
   sd.wait()
   sf.write('test.wav', audio, 16000)
   # Then manually transcribe
   ```

5. **Try simpler commands**
   - Test with short words: "click", "quit"
   - Avoid complex sentences

---

### 4. **Action Execution Issues**

#### Actions not executing (mouse not moving, clicks not working)

**Root Cause**: PyAutoGUI permissions or action bus not running

**Fix Priority Order**:

1. **Check if action bus is running**
   ```python
   # In actions.py, add debug:
   print(f"[DEBUG] Is running: {self.is_running}")
   print(f"[DEBUG] Is paused: {self.paused}")
   ```

2. **Check OS permissions**
   
   **Windows**:
   - Run Python as Administrator
   - Right-click Command Prompt → "Run as administrator"
   
   **macOS**:
   - System Preferences → Security & Privacy → Accessibility
   - Add Python/Terminal to allowed apps
   
   **Linux**:
   ```bash
   # May need to disable mouse grab
   # Or run without security restrictions:
   sudo python main.py
   ```

3. **Test PyAutoGUI directly**
   ```python
   import pyautogui
   import time
   
   # Move mouse
   pyautogui.moveTo(500, 500)
   time.sleep(0.5)
   
   # Click
   pyautogui.click()
   
   # Type
   pyautogui.typewrite('hello')
   ```

4. **Check if paused**
   - Open palm gesture sets PAUSE mode
   - Check console for "Control paused"
   - Say "resume" or show open palm again

5. **Disable failsafe** (in case mouse goes to corner)
   ```python
   import pyautogui
   pyautogui.FAILSAFE = False
   ```

---

#### Screen resolution mismatch (mouse goes to wrong location)

**Root Cause**: Screen resolution not detected correctly

**Fix Priority Order**:

1. **Check detected resolution**
   ```python
   import pyautogui
   width, height = pyautogui.size()
   print(f"Screen: {width}x{height}")
   ```

2. **Set resolution manually**
   - Edit `config.py`:
   ```python
   SCREEN_WIDTH = 1920   # Your actual width
   SCREEN_HEIGHT = 1080  # Your actual height
   ```

3. **Recalibrate gesture controller**
   - Edit `gesture_controller.py` line ~210:
   ```python
   x = int(index_tip[0] * SCREEN_WIDTH)
   y = int(index_tip[1] * SCREEN_HEIGHT)
   ```

---

### 5. **ML Model Issues**

#### Model training fails or accuracy is low

**Root Cause**: Insufficient training data, imbalanced classes, or hyperparameter issues

**Fix Priority Order**:

1. **Check data quality**
   ```bash
   # Check gesture_data.csv
   python -c "import pandas as pd; df = pd.read_csv('gesture_data.csv'); print(df['gesture'].value_counts())"
   ```
   - Should have ~50+ samples per gesture
   - All 4 classes should be present

2. **Collect more data**
   ```bash
   python collect_data.py --samples 100  # Collect 100 per gesture
   ```

3. **Try different model**
   ```bash
   python train_model.py --type svm  # Try SVM instead of RandomForest
   ```

4. **Adjust hyperparameters**
   - Edit `train_model.py` line ~150:
   ```python
   self.model = RandomForestClassifier(
       n_estimators=50,      # Try 50 or 200
       max_depth=10,         # Try 10-20
       min_samples_split=3,  # Try 2-5
   )
   ```

5. **Check confusion matrix**
   - Look at `confusion_matrix.png`
   - If classes are confused, collect more diverse data

---

#### Model inference is slow

**Root Cause**: RandomForest model size or CPU limitation

**Fix Priority Order**:

1. **Check inference time**
   ```python
   import time
   t0 = time.time()
   prediction = model.predict(features)
   print(f"Inference time: {(time.time() - t0) * 1000:.1f}ms")
   ```

2. **Reduce model size**
   ```bash
   # Train with fewer trees
   python train_model.py
   # Then in train_model.py, line 150:
   n_estimators=50  # Instead of 100
   ```

3. **Use SVM instead**
   ```bash
   python train_model.py --type svm
   ```

4. **Quantize model**
   - Convert to TFLite (advanced)

---

### 6. **Performance Issues**

#### High CPU usage or laggy video

**Root Cause**: High resolution, too many detections, or slow GPU

**Fix Priority Order**:

1. **Lower webcam resolution**
   ```python
   # Edit gesture_controller.py:
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```

2. **Reduce detection frequency**
   ```python
   # Edit gesture_controller.py line ~220:
   if frame_count % 2 == 0:  # Process every 2nd frame
       results = self.hands.process(rgb_frame)
   ```

3. **Disable FPS display**
   ```bash
   python main.py  # Don't show FPS
   ```

4. **Close other applications**
   - Close Chrome, Discord, Zoom, etc.

5. **Check CPU/RAM**
   - Windows: Task Manager
   - macOS: Activity Monitor
   - Linux: top, htop

---

## 📋 Debug Logging

Enable detailed logging:

```python
# In main.py, add at top:
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in config.py:
DEBUG = True
```

Then check console output for `[DEBUG]` messages.

---

## 🔧 Advanced Debugging

### Enable verbose MediaPipe logging
```python
import mediapipe as mp
mp.logging.set_verbosity(mp.logging.VerbosityLevel.DEBUG)
```

### Monitor action queue
```python
# In actions.py, modify executor loop:
while self.is_running:
    size = self.action_queue.qsize()
    if size > 0:
        print(f"[DEBUG] Queue size: {size}")
```

### Profile with cProfile
```bash
python -m cProfile -s cumtime main.py
```

---

## 📞 Getting Help

If issue persists:

1. **Note the error message** - Copy exact text
2. **Note your OS** - Windows 10/11, macOS 12+, Ubuntu 20.04, etc.
3. **Note Python version** - `python --version`
4. **Run `python setup_check.py`** - Attach output
5. **Share relevant code snippet** - If modified files

Then:
- Check GitHub Issues
- Create detailed bug report
- Include all information above

---

## ✅ Verification After Fix

After fixing an issue, verify:

```bash
# 1. Run setup check
python setup_check.py

# 2. Test gesture detection
python main.py
# Try moving hand, pinching, showing palm

# 3. Test voice (if applicable)
# Say: "click", "scroll", "what time is it"

# 4. Check for errors in console
# Should see no ERROR or exception messages
```

---

**Still stuck? Check README.md → Troubleshooting section for more solutions.**
