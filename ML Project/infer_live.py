"""
infer_live.py - Live gesture inference using trained ML model
Loads trained model and performs real-time gesture classification on webcam
"""

import cv2
import mediapipe as mp
import joblib
import numpy as np
import sys
from typing import Tuple, Optional, Dict
from actions import ActionBus, create_move_action, create_click_action, create_scroll_action, create_pause_action


class GestureInference:
    """Load and run inference with trained gesture model"""
    
    def __init__(self, model_path: str = "models/gesture_model.joblib"):
        """
        Initialize inference engine
        
        Args:
            model_path: Path to trained model
        """
        self.model_path = model_path
        self.model_data = None
        self.model = None
        self.label_encoder = None
        self.feature_columns = None
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # State
        self.prev_position = None
        self.confidence_threshold = 0.6
        
        # Load model
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load trained model"""
        try:
            print(f"[Inference] Loading model from {self.model_path}...")
            self.model_data = joblib.load(self.model_path)
            
            self.model = self.model_data['model']
            self.label_encoder = self.model_data['label_encoder']
            self.feature_columns = self.model_data['feature_columns']
            self.model_type = self.model_data.get('model_type', 'rf')
            
            print(f"[Inference] Model loaded successfully (type: {self.model_type})")
            print(f"[Inference] Gesture classes: {self.label_encoder.classes_}")
            return True
        except Exception as e:
            print(f"[Inference] Error loading model: {e}")
            return False
    
    def predict(self, landmarks: np.ndarray) -> Tuple[str, float]:
        """
        Predict gesture from landmarks
        
        Args:
            landmarks: Flattened hand landmarks (1x63)
            
        Returns:
            Tuple of (gesture_name, confidence)
        """
        try:
            # Ensure correct shape
            landmarks = landmarks.reshape(1, -1)
            
            # Predict
            prediction = self.model.predict(landmarks)[0]
            
            # Get confidence
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(landmarks)[0]
                confidence = probabilities.max()
            else:
                confidence = 1.0  # Some models don't have predict_proba
            
            # Decode gesture name
            gesture_name = self.label_encoder.inverse_transform([prediction])[0]
            
            return gesture_name, float(confidence)
        except Exception as e:
            print(f"[Inference] Prediction error: {e}")
            return "unknown", 0.0
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[str], float]:
        """
        Process frame and perform inference
        
        Args:
            frame: Input video frame (BGR)
            
        Returns:
            Annotated frame, predicted gesture, and confidence
        """
        # Flip for selfie view
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect hands
        results = self.hands.process(rgb_frame)
        
        gesture_name = None
        confidence = 0.0
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Extract landmarks
                landmarks = np.array([(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark])
                
                # Flatten for model
                landmarks_flat = landmarks.flatten()
                
                # Predict
                gesture_name, confidence = self.predict(landmarks_flat)
                
                # Draw landmarks
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Get index finger position for mouse move
                if gesture_name == 'move':
                    index_tip = landmarks[8]
                    x = int(index_tip[0] * 1920)
                    y = int(index_tip[1] * 1080)
                    self.prev_position = (x, y)
        
        # Draw info
        info_text = f"Gesture: {gesture_name if gesture_name else 'No hand detected'}"
        conf_text = f"Confidence: {confidence:.2f}" if gesture_name else ""
        
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, conf_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 0), 2)
        
        # Confidence threshold warning
        if gesture_name and confidence < self.confidence_threshold:
            cv2.putText(frame, "Low confidence!", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        cv2.putText(frame, "Press Q to quit", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return cv2.flip(frame, 1), gesture_name, confidence
    
    def run_inference(self, action_bus: Optional[ActionBus] = None):
        """
        Run live inference on webcam
        
        Args:
            action_bus: Optional ActionBus to send actions
        """
        if self.model is None:
            print("[Inference] Model not loaded!")
            return
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[Inference] Error: Cannot open webcam")
            return
        
        print("[Inference] Starting live inference... Press Q to quit")
        
        gesture_history = []
        smoothing_window = 5  # Smooth predictions over 5 frames
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                annotated_frame, gesture, confidence = self.process_frame(frame)
                
                # Smooth predictions
                if gesture and confidence > self.confidence_threshold:
                    gesture_history.append(gesture)
                    if len(gesture_history) > smoothing_window:
                        gesture_history.pop(0)
                    
                    # Use majority vote for smoothing
                    if gesture_history:
                        smoothed_gesture = max(set(gesture_history), key=gesture_history.count)
                        
                        # Send action if we have action bus
                        if action_bus:
                            self._send_action(action_bus, smoothed_gesture)
                
                cv2.imshow("Gesture Inference", annotated_frame)
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # Q or ESC
                    break
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    @staticmethod
    def _send_action(action_bus: ActionBus, gesture: str):
        """Send action to action bus based on gesture"""
        if gesture == "move":
            # Mouse move would be handled continuously
            pass
        elif gesture == "click":
            action = create_click_action(source="ml_gesture")
            action_bus.enqueue(action)
        elif gesture == "scroll":
            action = create_scroll_action(direction="up", source="ml_gesture")
            action_bus.enqueue(action)
        elif gesture == "pause":
            action = create_pause_action(source="ml_gesture")
            action_bus.enqueue(action)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Live gesture inference with trained model")
    parser.add_argument("--model", type=str, default="models/gesture_model.joblib", help="Path to trained model")
    parser.add_argument("--threshold", type=float, default=0.6, help="Confidence threshold (0-1)")
    parser.add_argument("--with-actions", action="store_true", help="Send actions to action bus")
    
    args = parser.parse_args()
    
    # Create inference engine
    inference = GestureInference(model_path=args.model)
    inference.confidence_threshold = args.threshold
    
    if inference.model is None:
        print("[Main] Failed to load model. Exiting.")
        sys.exit(1)
    
    # Create action bus if requested
    action_bus = None
    if args.with_actions:
        action_bus = ActionBus()
        action_bus.start()
    
    try:
        inference.run_inference(action_bus=action_bus)
    except KeyboardInterrupt:
        print("\n[Main] Interrupted")
    finally:
        if action_bus:
            action_bus.stop()


if __name__ == "__main__":
    main()
