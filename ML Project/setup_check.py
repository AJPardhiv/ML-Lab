"""
Quick Start Guide - Gesture-Based Laptop Controller
Run this script to set up and test the system
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")


def check_requirements():
    """Check if all requirements are installed"""
    print_header("1. CHECKING PYTHON DEPENDENCIES")
    
    required_packages = {
        "cv2": "opencv-python",
        "mediapipe": "mediapipe",
        "pyautogui": "pyautogui",
        "pyttsx3": "pyttsx3",
        "numpy": "numpy",
        "sklearn": "scikit-learn",
        "joblib": "joblib"
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n  Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("  ✓ Installation complete")
    else:
        print("\n  ✓ All dependencies installed")
    
    return len(missing) == 0


def check_vosk_model():
    """Check if Vosk model is available"""
    print_header("2. CHECKING VOSK MODEL")
    
    model_path = Path("model")
    
    if model_path.exists() and (model_path / "conf" / "model.conf").exists():
        print(f"  ✓ Vosk model found at: {model_path.absolute()}")
        return True
    
    print("  ✗ Vosk model NOT found")
    print("\n  To enable voice assistant, download Vosk model:")
    print("\n  Option 1: Automatic (PowerShell on Windows):")
    print("    $url = 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.42-gigaspeech.zip'")
    print("    Invoke-WebRequest $url -O vosk-model.zip")
    print("    Expand-Archive vosk-model.zip -DestinationPath .")
    print("    Rename-Item vosk-model-en-us-0.42-gigaspeech model")
    print("    Remove-Item vosk-model.zip")
    
    print("\n  Option 2: Manual:")
    print("    1. Visit: https://alphacephei.com/vosk/models")
    print("    2. Download: vosk-model-en-us-0.42-gigaspeech.zip")
    print("    3. Extract to: model/")
    print("    4. Verify: model/conf/model.conf should exist")
    
    print("\n  Gesture control will work without Vosk.")
    print("  Voice assistant requires the model.")
    
    return False


def check_webcam():
    """Check if webcam is available"""
    print_header("3. CHECKING WEBCAM")
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("  ✓ Webcam detected and working")
                h, w, c = frame.shape
                print(f"    Resolution: {w}x{h}")
                return True
    except Exception as e:
        print(f"  ✗ Webcam error: {e}")
    
    print("  ✗ Webcam NOT detected")
    print("\n  Troubleshooting:")
    print("    1. Plug in USB camera (if not built-in)")
    print("    2. Check camera is not in use by another app")
    print("    3. Check camera permissions in OS settings")
    print("    4. Try: python -c \"import cv2; print(cv2.VideoCapture(0).isOpened())\"")
    
    return False


def check_microphone():
    """Check if microphone is available"""
    print_header("4. CHECKING MICROPHONE")
    
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        devices = p.get_device_count()
        p.terminate()
        
        if devices > 0:
            print(f"  ✓ Microphone detected ({devices} audio devices)")
            return True
    except Exception as e:
        print(f"  ✗ Microphone error: {e}")
    
    print("  ✗ Microphone NOT detected")
    print("\n  Troubleshooting:")
    print("    1. Plug in USB microphone")
    print("    2. Check microphone permissions")
    print("    3. Test in OS sound settings")
    
    return False


def check_os_permissions():
    """Check OS-specific permissions"""
    print_header("5. CHECKING OS PERMISSIONS")
    
    import platform
    os_name = platform.system()
    
    if os_name == "Windows":
        print("  Windows detected")
        print("  ⚠  PyAutoGUI may require administrator privileges")
        print("    If actions don't work, try:")
        print("    1. Run Command Prompt as Administrator")
        print("    2. cd to project folder")
        print("    3. python main.py")
        print("  ✓ Ready to run")
    
    elif os_name == "Darwin":  # macOS
        print("  macOS detected")
        print("  ⚠  Camera/Microphone permissions required:")
        print("    System Preferences → Security & Privacy → Camera/Microphone")
        print("  ⚠  PyAutoGUI requires Accessibility permissions:")
        print("    System Preferences → Security & Privacy → Accessibility")
        print("  ! First run will prompt for permissions")
        print("  ✓ Ready to run")
    
    elif os_name == "Linux":
        print("  Linux detected")
        print("  ⚠  Input device permissions may be required:")
        print("    sudo usermod -a -G input $USER")
        print("    (logout and login for changes to take effect)")
        print("  ✓ Ready to run")
    
    return True


def create_directories():
    """Create necessary directories"""
    print_header("6. CREATING DIRECTORIES")
    
    dirs = ["models", "data"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
        print(f"  ✓ {d}/")
    
    return True


def run_self_test():
    """Run self-test of gesture detection"""
    print_header("7. SELF-TEST: GESTURE DETECTION")
    
    print("  Starting gesture detection test...")
    print("  A webcam window will open for 10 seconds")
    print("  Move your hand and confirm gesture detection works\n")
    
    try:
        import cv2
        from gesture_controller import GestureController
        from actions import ActionBus
        
        action_bus = ActionBus()
        action_bus.start()
        
        controller = GestureController(action_bus=action_bus)
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("  ✗ Cannot open webcam")
            return False
        
        print("  Testing for 10 seconds...")
        fps_counter = 0
        
        for i in range(600):  # 10 seconds at 60 FPS
            ret, frame = cap.read()
            if not ret:
                break
            
            annotated_frame, gesture = controller.process_frame(frame)
            
            if gesture:
                print(f"  ✓ Detected gesture: {gesture}")
            
            cv2.imshow("Gesture Detection Test", annotated_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            fps_counter += 1
        
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\n  ✓ Self-test complete ({fps_counter} frames processed)")
        return True
    
    except Exception as e:
        print(f"  ✗ Self-test failed: {e}")
        return False


def print_next_steps():
    """Print next steps for user"""
    print_header("NEXT STEPS")
    
    print("  1. RULE-BASED GESTURE CONTROL (No ML training):")
    print("     python main.py")
    
    print("\n  2. ML-BASED GESTURE CONTROL (Train custom model):")
    print("     # Collect training data:")
    print("     python collect_data.py")
    print("     ")
    print("     # Train model:")
    print("     python train_model.py --type rf")
    print("     ")
    print("     # Run with model:")
    print("     python main.py --ml --model models/gesture_model.joblib")
    
    print("\n  3. INFERENCE ONLY (Test model):")
    print("     python infer_live.py --model models/gesture_model.joblib")
    
    print("\n  4. VOICE CONTROLS:")
    print("     Say 'start gestures' to enable gesture control")
    print("     Say 'click', 'scroll', 'open youtube', etc.")


def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("  GESTURE-BASED LAPTOP CONTROLLER - SETUP CHECK")
    print("="*60)
    
    checks = [
        ("Dependencies", check_requirements),
        ("Vosk Model", check_vosk_model),
        ("Webcam", check_webcam),
        ("Microphone", check_microphone),
        ("OS Permissions", check_os_permissions),
        ("Directories", create_directories),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[name] = False
    
    # Summary
    print_header("SETUP SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"  Checks passed: {passed}/{total}\n")
    
    for name, result in results.items():
        status = "✓" if result else "⚠"
        print(f"  {status} {name}")
    
    if passed == total:
        print("\n  ✓ ALL CHECKS PASSED - System is ready!")
    else:
        print("\n  ⚠  Some checks failed - see above for details")
        print("    Gesture control will still work without microphone/Vosk")
    
    print_next_steps()
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
