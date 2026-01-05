"""
config.py - Configuration constants and settings
Centralized configuration for gesture and voice parameters
"""

# ============================================================================
# GESTURE CONTROLLER CONFIGURATION
# ============================================================================

GESTURE_CONFIG = {
    # Hand detection thresholds
    "min_detection_confidence": 0.7,      # MediaPipe hand detection confidence
    "min_tracking_confidence": 0.5,       # Hand tracking confidence
    
    # Gesture sensitivity
    "pinch_threshold": 0.05,              # Distance between thumb and index for pinch
    "palm_threshold": 0.1,                # For detecting open palm
    "finger_up_threshold": 0.1,           # For detecting extended fingers
    "scroll_distance_threshold": 0.08,    # For two-finger scroll detection
    
    # Timing
    "gesture_cooldown": 0.3,              # Seconds between gesture detections
    "frame_skip": 0,                      # Skip N frames for performance
    
    # Display
    "show_fps": True,
    "show_hand_labels": True,
}

# ============================================================================
# VOICE ASSISTANT CONFIGURATION
# ============================================================================

VOICE_CONFIG = {
    # Vosk STT settings
    "vosk_model_path": "model",
    "sample_rate": 16000,
    "audio_chunk_size": 4096,
    "listen_timeout": 5.0,               # Seconds to listen
    
    # TTS settings
    "tts_rate": 150,                      # Words per minute
    "tts_voice_id": 0,                    # 0=default, 1=alternative
    "tts_async": True,                    # Use background thread for TTS
    
    # Command matching
    "fuzzy_match_threshold": 0.8,         # Similarity threshold for command matching
    "enable_confirmation": False,         # Ask user to confirm low-confidence commands
    
    # Keywords for voice recognition
    "custom_keywords": [
        "start", "stop", "click", "double", "scroll", "up", "down",
        "type", "open", "youtube", "google", "time", "quit", "pause", "resume"
    ]
}

# ============================================================================
# ACTION BUS CONFIGURATION
# ============================================================================

ACTION_CONFIG = {
    "queue_timeout": 0.1,                 # Timeout for queue.get()
    "action_timeout": 5.0,                # Max execution time per action
    "enable_logging": True,               # Log all actions
    "enable_voice_feedback": True,        # Provide TTS feedback
}

# ============================================================================
# PYAUTOGUI CONFIGURATION
# ============================================================================

PYAUTOGUI_CONFIG = {
    "failsafe": False,                    # Disable failsafe (mouse to corner)
    "click_interval": 0.1,                # Pause between multi-clicks
    "scroll_pause": 0.1,                  # Pause after scroll
    "typewrite_interval": 0.05,           # Interval between keypresses
}

# ============================================================================
# ML MODEL CONFIGURATION
# ============================================================================

ML_CONFIG = {
    # Data collection
    "samples_per_gesture": 50,            # Minimum samples per gesture class
    "data_csv_path": "gesture_data.csv",
    
    # Training
    "test_split": 0.2,                    # 20% test, 80% train
    "random_state": 42,
    "model_type": "rf",                   # "rf" (RandomForest) or "svm"
    "model_output_path": "models/gesture_model.joblib",
    
    # RandomForest hyperparameters
    "rf_n_estimators": 100,
    "rf_max_depth": 15,
    "rf_min_samples_split": 5,
    "rf_min_samples_leaf": 2,
    
    # SVM hyperparameters
    "svm_kernel": "rbf",
    "svm_C": 1.0,
    "svm_gamma": "scale",
    
    # Inference
    "inference_confidence_threshold": 0.6,
    "gesture_smoothing_window": 5,        # Smooth predictions over N frames
}

# ============================================================================
# GESTURE MAPPING
# ============================================================================

GESTURE_MAP = {
    "MOVE": {
        "description": "Move mouse cursor",
        "action_type": "move_mouse",
        "icon": "👆"
    },
    "CLICK": {
        "description": "Single click",
        "action_type": "click",
        "icon": "☝️"
    },
    "DOUBLE_CLICK": {
        "description": "Double click",
        "action_type": "double_click",
        "icon": "☝️☝️"
    },
    "DRAG": {
        "description": "Drag action",
        "action_type": "drag",
        "icon": "✌️"
    },
    "SCROLL": {
        "description": "Scroll up or down",
        "action_type": "scroll",
        "icon": "🤘"
    },
    "PAUSE": {
        "description": "Pause/resume control",
        "action_type": "pause",
        "icon": "✋"
    }
}

# ============================================================================
# VOICE COMMAND MAPPING
# ============================================================================

VOICE_COMMANDS = {
    "start gestures": {
        "action": "start_gestures",
        "feedback": "Gesture control enabled"
    },
    "stop gestures": {
        "action": "stop_gestures",
        "feedback": "Gesture control disabled"
    },
    "click": {
        "action": "click",
        "feedback": "Clicked"
    },
    "double click": {
        "action": "double_click",
        "feedback": "Double clicked"
    },
    "scroll up": {
        "action": "scroll_up",
        "feedback": "Scrolling up"
    },
    "scroll down": {
        "action": "scroll_down",
        "feedback": "Scrolling down"
    },
    "type": {
        "action": "type_text",
        "feedback": "Ready to type"
    },
    "open youtube": {
        "action": "open_youtube",
        "feedback": "Opening YouTube"
    },
    "open google": {
        "action": "open_google",
        "feedback": "Opening Google"
    },
    "what time is it": {
        "action": "get_time",
        "feedback": "Checking time"
    },
    "pause": {
        "action": "pause",
        "feedback": "Control paused"
    },
    "resume": {
        "action": "resume",
        "feedback": "Control resumed"
    },
    "quit": {
        "action": "quit",
        "feedback": "Goodbye"
    }
}

# ============================================================================
# SCREEN RESOLUTION (Set based on your monitor)
# ============================================================================

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Auto-detect if possible:
try:
    import pyautogui
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
except:
    pass  # Use defaults

# ============================================================================
# DEBUG / LOGGING
# ============================================================================

DEBUG = False  # Set to True for verbose logging

if DEBUG:
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    )
