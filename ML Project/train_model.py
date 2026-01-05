"""
train_model.py - Train gesture classification model
Reads collected gesture data and trains RandomForest model
"""

import pandas as pd
import numpy as np
import joblib
import sys
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


class GestureModelTrainer:
    """Train gesture classification model"""
    
    def __init__(self, data_csv: str = "gesture_data.csv", model_type: str = "rf"):
        """
        Initialize trainer
        
        Args:
            data_csv: Path to collected gesture data CSV
            model_type: Model type - 'rf' (RandomForest) or 'svm'
        """
        self.data_csv = data_csv
        self.model_type = model_type
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_columns = None
        self.gesture_classes = None
    
    def load_data(self) -> bool:
        """Load and validate data"""
        try:
            print(f"[Trainer] Loading data from {self.data_csv}...")
            self.df = pd.read_csv(self.data_csv)
            
            print(f"[Trainer] Data shape: {self.df.shape}")
            print(f"[Trainer] Gesture distribution:")
            print(self.df['gesture'].value_counts())
            
            # Check for sufficient data
            if len(self.df) < 100:
                print("[Trainer] Warning: Less than 100 samples. Model may not train well.")
            
            self.gesture_classes = self.df['gesture'].unique()
            print(f"[Trainer] Gesture classes: {self.gesture_classes}")
            
            return True
        except Exception as e:
            print(f"[Trainer] Error loading data: {e}")
            return False
    
    def prepare_features(self) -> tuple:
        """Prepare features and labels"""
        try:
            print("[Trainer] Preparing features...")
            
            # Extract features (all columns except 'gesture')
            self.feature_columns = [col for col in self.df.columns if col != 'gesture']
            X = self.df[self.feature_columns].values
            
            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            
            # Encode labels
            y = self.label_encoder.fit_transform(self.df['gesture'])
            
            print(f"[Trainer] Features shape: {X.shape}")
            print(f"[Trainer] Classes: {dict(zip(self.label_encoder.classes_, range(len(self.label_encoder.classes_))))}")
            
            return X, y
        except Exception as e:
            print(f"[Trainer] Error preparing features: {e}")
            return None, None
    
    def train(self, test_size: float = 0.2, random_state: int = 42):
        """
        Train the model
        
        Args:
            test_size: Proportion of data for testing
            random_state: Random seed
        """
        # Load and prepare data
        if not self.load_data():
            return False
        
        X, y = self.prepare_features()
        if X is None or y is None:
            return False
        
        # Split data
        print(f"[Trainer] Splitting data ({100*test_size:.0f}% test)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        print(f"[Trainer] Train size: {X_train.shape[0]}, Test size: {X_test.shape[0]}")
        
        # Train model
        print(f"[Trainer] Training {self.model_type.upper()} model...")
        
        if self.model_type == "rf":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1,
                verbose=1
            )
        elif self.model_type == "svm":
            self.model = SVC(
                kernel='rbf',
                C=1.0,
                gamma='scale',
                probability=True,
                verbose=1
            )
        else:
            print(f"[Trainer] Unknown model type: {self.model_type}")
            return False
        
        self.model.fit(X_train, y_train)
        print("[Trainer] Training complete!")
        
        # Evaluate
        print("\n[Trainer] ===== EVALUATION =====")
        self._evaluate(self.model, X_train, X_test, y_train, y_test)
        
        return True
    
    def _evaluate(self, model, X_train, X_test, y_train, y_test):
        """Evaluate model performance"""
        # Train predictions
        y_train_pred = model.predict(X_train)
        train_acc = accuracy_score(y_train, y_train_pred)
        
        # Test predictions
        y_test_pred = model.predict(X_test)
        test_acc = accuracy_score(y_test, y_test_pred)
        
        print(f"Training Accuracy: {train_acc:.4f}")
        print(f"Test Accuracy:     {test_acc:.4f}")
        
        # Detailed metrics
        print("\nTest Set Metrics:")
        print(f"Precision: {precision_score(y_test, y_test_pred, average='weighted'):.4f}")
        print(f"Recall:    {recall_score(y_test, y_test_pred, average='weighted'):.4f}")
        print(f"F1-Score:  {f1_score(y_test, y_test_pred, average='weighted'):.4f}")
        
        # Confusion matrix
        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_test_pred)
        
        # Print confusion matrix nicely
        gesture_names = self.label_encoder.classes_
        print("\n       ", end="")
        for name in gesture_names:
            print(f"{name:>8}", end="")
        print()
        
        for i, name in enumerate(gesture_names):
            print(f"{name:>8}", end=" ")
            for j in range(len(gesture_names)):
                print(f"{cm[i, j]:>8}", end=" ")
            print()
        
        # Plot confusion matrix
        try:
            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                       xticklabels=gesture_names,
                       yticklabels=gesture_names)
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            plt.title('Gesture Classification Confusion Matrix')
            plt.tight_layout()
            plt.savefig('confusion_matrix.png', dpi=100)
            print("\n[Trainer] Confusion matrix saved to confusion_matrix.png")
        except Exception as e:
            print(f"[Trainer] Could not save confusion matrix plot: {e}")
    
    def save_model(self, model_path: str = "models/gesture_model.joblib"):
        """Save trained model"""
        if self.model is None:
            print("[Trainer] No model to save")
            return False
        
        try:
            # Create directory if needed
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save model and label encoder together
            model_data = {
                'model': self.model,
                'label_encoder': self.label_encoder,
                'feature_columns': self.feature_columns,
                'gesture_classes': self.gesture_classes,
                'model_type': self.model_type
            }
            
            joblib.dump(model_data, model_path)
            print(f"[Trainer] Model saved to {model_path}")
            return True
        except Exception as e:
            print(f"[Trainer] Error saving model: {e}")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train gesture classification model")
    parser.add_argument("--data", type=str, default="gesture_data.csv", help="Input data CSV")
    parser.add_argument("--output", type=str, default="models/gesture_model.joblib", help="Output model path")
    parser.add_argument("--type", type=str, default="rf", choices=['rf', 'svm'], help="Model type (rf or svm)")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set size (0-1)")
    
    args = parser.parse_args()
    
    # Train
    trainer = GestureModelTrainer(data_csv=args.data, model_type=args.type)
    
    if trainer.train(test_size=args.test_size):
        trainer.save_model(model_path=args.output)
        print("\n[Trainer] Model training successful!")
    else:
        print("\n[Trainer] Model training failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
