"""
collect_data.py - Collect hand gesture training data
Records MediaPipe hand landmarks to CSV file for ML model training
"""

import cv2
import mediapipe as mp
import csv
import os
import sys
import time
from typing import List, Tuple
import numpy as np


class GestureDataCollector:
    """Collects hand gesture landmark data for training"""
    
    GESTURES = {
        '1': 'move',
        '2': 'click',
        '3': 'scroll',
        '4': 'pause'
    }
    
    def __init__(self, output_csv: str = "gesture_data.csv"):
        """
        Initialize data collector
        
        Args:
            output_csv: Output CSV file path
        """
        self.output_csv = output_csv
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Data storage
        self.data = []
        self.samples_per_gesture = 50  # Number of samples to collect per gesture
        
        # Create CSV file with headers if doesn't exist
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers"""
        if os.path.exists(self.output_csv):
            print(f"[DataCollector] Appending to existing file: {self.output_csv}")
            return
        
        # Create headers: 21 landmarks * 3 coordinates (x, y, z) + label
        headers = []
        for i in range(21):
            headers.extend([f"landmark_{i}_x", f"landmark_{i}_y", f"landmark_{i}_z"])
        headers.append("gesture")
        
        with open(self.output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        print(f"[DataCollector] Created CSV: {self.output_csv}")
    
    def collect(self):
        """Start interactive data collection"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[DataCollector] Error: Cannot open webcam")
            return
        
        print("\n[DataCollector] ===== HAND GESTURE DATA COLLECTION =====")
        print("[DataCollector] Instructions:")
        for key, gesture in self.GESTURES.items():
            print(f"  Press '{key}' to collect '{gesture}' samples")
        print("  Press 'Q' to exit")
        print("[DataCollector] =============================================\n")
        
        current_gesture = None
        current_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip for selfie view
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect hands
            results = self.hands.process(rgb_frame)
            
            # Draw landmarks
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    # If collecting, save data
                    if current_gesture:
                        landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                        self._save_sample(landmarks, current_gesture)
                        current_count += 1
                        
                        if current_count >= self.samples_per_gesture:
                            print(f"[DataCollector] Completed {self.samples_per_gesture} samples for '{current_gesture}'")
                            current_gesture = None
                            current_count = 0
            
            # Display info
            info_text = f"Gesture: {current_gesture if current_gesture else 'None'}"
            count_text = f"Samples: {current_count}/{self.samples_per_gesture}" if current_gesture else ""
            
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, count_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 0), 2)
            
            # Display controls
            controls_y = 110
            for key, gesture in self.GESTURES.items():
                color = (0, 255, 0) if current_gesture == gesture else (200, 200, 200)
                cv2.putText(frame, f"[{key}] {gesture}", (10, controls_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                controls_y += 30
            
            cv2.imshow("Gesture Data Collector", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif chr(key) in self.GESTURES:
                gesture = self.GESTURES[chr(key)]
                if current_gesture != gesture:
                    current_gesture = gesture
                    current_count = 0
                    print(f"[DataCollector] Started collecting '{gesture}'...")
        
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"[DataCollector] Data collection complete. Saved to {self.output_csv}")
        print(f"[DataCollector] Total samples: {len(self.data)}")
    
    def _save_sample(self, landmarks: List[Tuple[float, float, float]], gesture: str):
        """Save a single sample to CSV"""
        try:
            # Flatten landmarks
            row = []
            for x, y, z in landmarks:
                row.extend([x, y, z])
            row.append(gesture)
            
            # Append to CSV
            with open(self.output_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            self.data.append(row)
        except Exception as e:
            print(f"[DataCollector] Error saving sample: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect hand gesture training data")
    parser.add_argument("--output", type=str, default="gesture_data.csv", help="Output CSV file")
    parser.add_argument("--samples", type=int, default=50, help="Samples per gesture")
    
    args = parser.parse_args()
    
    collector = GestureDataCollector(output_csv=args.output)
    collector.samples_per_gesture = args.samples
    
    try:
        collector.collect()
    except KeyboardInterrupt:
        print("\n[DataCollector] Interrupted")
    except Exception as e:
        print(f"[DataCollector] Error: {e}")


if __name__ == "__main__":
    main()
