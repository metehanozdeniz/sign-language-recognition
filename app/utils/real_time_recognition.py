#!/usr/bin/env python3
"""
Real-time Sign Language Recognition using MediaPipe and LSTM model
Flask-compatible version for web streaming
"""

import cv2
import numpy as np
import mediapipe as mp
import json
import joblib
from collections import deque
import tensorflow as tf
from tensorflow.keras.models import load_model
import warnings
import threading
import time

warnings.filterwarnings("ignore")


class RealTimeSignLanguageRecognizer:
    def __init__(
        self,
        model_path="app/model/sign_language_recognition.keras",
        scaler_path="app/model/scaler.pkl",
        label_encoder_path="app/model/label_encoder.pkl",
        feature_order_path="app/model/feature_order.json",
        cam_id=2,  # Default camera ID (0 for default camera)
    ):
        # Load model and preprocessing tools
        print("Loading model and preprocessing tools...")
        self.model = load_model(model_path)
        self.scaler = joblib.load(scaler_path)
        self.label_encoder = joblib.load(label_encoder_path)

        with open(feature_order_path, "r") as f:
            self.feature_order = json.load(f)

        # MediaPipe setup - will be initialized when starting
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = None
        self.pose = None

        # Parameters
        self.fps = 15  # Target FPS for feature extraction
        self.window_sec = 0.5  # Window size in seconds
        self.window_size = int(self.fps * self.window_sec)  # Frames per window
        self.sequence_length = 5  # Number of windows for LSTM
        self.CAM_ID = cam_id  # Camera ID

        # Buffers
        self.frame_buffer = deque(maxlen=self.window_size)
        self.feature_buffer = deque(maxlen=self.sequence_length)

        # Landmark indices
        self.finger_tips = [4, 8, 12, 16, 20]
        self.pose_joints = [11, 12, 13, 14, 15, 16]

        # For FPS calculation
        self.frame_count = 0
        self.fps_timer = cv2.getTickCount()

        # Video capture
        self.cap = None
        self.is_running = False

        # Current predictions
        self.current_prediction = None
        self.top3_predictions = None
        self.lock = threading.Lock()

        print("Initialization complete!")

    def _init_mediapipe(self):
        """Initialize MediaPipe models"""
        if self.hands is None:
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        if self.pose is None:
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

    def _cleanup_mediapipe(self):
        """Clean up MediaPipe models"""
        if self.hands:
            self.hands.close()
            self.hands = None
        if self.pose:
            self.pose.close()
            self.pose = None

    def start_capture(self):
        """Start video capture"""
        try:
            if self.cap is None or not self.cap.isOpened():
                # Try different camera indices if default fails
                for cam_idx in [self.CAM_ID, 0, 1, 2]:
                    self.cap = cv2.VideoCapture(cam_idx)
                    if self.cap.isOpened():
                        print(f"Camera opened successfully at index {cam_idx}")
                        break
                else:
                    print("Failed to open any camera")
                    return False

                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Initialize MediaPipe
            self._init_mediapipe()

            # Clear buffers
            self.frame_buffer.clear()
            self.feature_buffer.clear()

            self.is_running = True
            return True
        except Exception as e:
            print(f"Error starting capture: {e}")
            return False

    def stop_capture(self):
        """Stop video capture and release resources"""
        self.is_running = False

        # Clean up MediaPipe
        self._cleanup_mediapipe()

        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None

        # Clear predictions
        with self.lock:
            self.current_prediction = None
            self.top3_predictions = None

    def extract_landmarks_from_frame(self, frame):
        """Extract hand and pose landmarks from a single frame"""
        if self.hands is None or self.pose is None:
            return {"hand_0": [], "hand_1": [], "pose": []}, None, None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process with MediaPipe
        hands_results = self.hands.process(frame_rgb)
        pose_results = self.pose.process(frame_rgb)

        landmarks = {
            "hand_0": [],  # First detected hand
            "hand_1": [],  # Second detected hand
            "pose": [],
        }

        # Extract hand landmarks - use detection order as in training
        if hands_results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(
                hands_results.multi_hand_landmarks
            ):
                if hand_idx > 1:  # Only process first 2 hands
                    break

                # Extract fingertip landmarks
                for lm_idx in self.finger_tips:
                    lm = hand_landmarks.landmark[lm_idx]
                    landmarks[f"hand_{hand_idx}"].append(
                        {"x": lm.x, "y": lm.y, "z": lm.z}
                    )

        # Extract pose landmarks
        if pose_results.pose_landmarks:
            for idx in self.pose_joints:
                lm = pose_results.pose_landmarks.landmark[idx]
                landmarks["pose"].append({"x": lm.x, "y": lm.y, "z": lm.z})

        return landmarks, hands_results, pose_results

    def extract_window_features(self, window_landmarks):
        """Extract features from a window of landmarks"""
        features = {}

        # Initialize all features to 0
        for feature_name in self.feature_order:
            features[feature_name] = 0.0

        # Pose features (joints)
        pose_coords = {"x": [], "y": [], "z": []}
        for frame_landmarks in window_landmarks:
            for lm in frame_landmarks["pose"]:
                pose_coords["x"].append(lm["x"])
                pose_coords["y"].append(lm["y"])
                pose_coords["z"].append(lm["z"])

        for axis in ["x", "y", "z"]:
            if pose_coords[axis]:
                features[f"joints_{axis}_mean"] = float(np.mean(pose_coords[axis]))
                features[f"joints_{axis}_std"] = float(np.std(pose_coords[axis]))

        # Hand features - matching training data convention
        # hand_0 -> left features, hand_1 -> right features
        for hand_idx, feature_prefix in [(0, "left"), (1, "right")]:
            hand_coords = {"x": [], "y": [], "z": []}
            for frame_landmarks in window_landmarks:
                for lm in frame_landmarks[f"hand_{hand_idx}"]:
                    hand_coords["x"].append(lm["x"])
                    hand_coords["y"].append(lm["y"])
                    hand_coords["z"].append(lm["z"])

            for axis in ["x", "y", "z"]:
                if hand_coords[axis]:
                    features[f"{feature_prefix}_tips_{axis}_mean"] = float(
                        np.mean(hand_coords[axis])
                    )
                    features[f"{feature_prefix}_tips_{axis}_std"] = float(
                        np.std(hand_coords[axis])
                    )

        # Ensure features are in correct order
        ordered_features = [features[name] for name in self.feature_order]
        return np.array(ordered_features)

    def predict(self):
        """Make prediction if we have enough windows"""
        if len(self.feature_buffer) < self.sequence_length:
            return None, None

        # Prepare input
        X = np.array(list(self.feature_buffer))
        X = X.reshape(1, self.sequence_length, -1)

        # Scale features
        X_reshaped = X.reshape(X.shape[1], -1)
        X_scaled = self.scaler.transform(X_reshaped)
        X = X_scaled.reshape(1, X.shape[1], -1)

        # Predict
        predictions = self.model.predict(X, verbose=0)[0]

        # Get top 3 predictions
        top3_indices = np.argsort(predictions)[-3:][::-1]
        top3_labels = self.label_encoder.inverse_transform(top3_indices)
        top3_confidences = predictions[top3_indices]

        predicted_class = top3_indices[0]
        predicted_label = top3_labels[0]

        return predicted_label, list(zip(top3_labels, top3_confidences * 100))

    def draw_landmarks(self, frame, hands_results, pose_results):
        """Draw MediaPipe landmarks on frame"""
        # Draw hand landmarks
        if hands_results and hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=2, circle_radius=2
                    ),
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                )

        # Draw pose landmarks
        if pose_results and pose_results.pose_landmarks:
            # Only draw the joints we use
            for idx in self.pose_joints:
                lm = pose_results.pose_landmarks.landmark[idx]
                h, w = frame.shape[:2]
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

        return frame

    def get_frame(self):
        """Get a single processed frame for streaming"""
        if not self.is_running:
            # Return a placeholder frame when not running
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                placeholder,
                "Camera Stopped",
                (200, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            return placeholder

        if not self.cap or not self.cap.isOpened():
            # Try to restart capture
            if not self.start_capture():
                # Return error frame
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    error_frame,
                    "Camera Error",
                    (220, 240),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )
                return error_frame

        ret, frame = self.cap.read()
        if not ret:
            return None

        # Extract landmarks
        landmarks, hands_results, pose_results = self.extract_landmarks_from_frame(
            frame
        )

        # Add to buffer
        self.frame_buffer.append(landmarks)

        # Extract features when window is full
        if len(self.frame_buffer) == self.window_size:
            features = self.extract_window_features(list(self.frame_buffer))
            self.feature_buffer.append(features)
            self.frame_buffer.clear()

        # Make prediction
        predicted_label, top3 = self.predict()

        # Update current predictions
        with self.lock:
            self.current_prediction = predicted_label
            self.top3_predictions = top3

        # Draw landmarks
        frame = self.draw_landmarks(frame, hands_results, pose_results)

        # Display prediction on frame
        if predicted_label:
            # Main prediction
            cv2.putText(
                frame,
                f"Prediction: {predicted_label}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

            # Top 3 predictions
            y_offset = 60
            for i, (label, conf) in enumerate(top3):
                text = f"{i + 1}. {label}: {conf:.1f}%"
                cv2.putText(
                    frame,
                    text,
                    (10, y_offset + i * 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                )
        else:
            cv2.putText(
                frame,
                "Collecting frames...",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

        # Calculate and display FPS
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            current_time = cv2.getTickCount()
            fps = 30 / ((current_time - self.fps_timer) / cv2.getTickFrequency())
            self.fps_timer = current_time
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (540, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2,
            )

        return frame

    def get_current_predictions(self):
        """Get current predictions thread-safely"""
        with self.lock:
            return self.current_prediction, self.top3_predictions


# Global instance
recognizer = None


def get_recognizer():
    """Get or create the global recognizer instance"""
    global recognizer
    if recognizer is None:
        recognizer = RealTimeSignLanguageRecognizer()
    return recognizer
