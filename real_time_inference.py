import cv2
import pandas as pd
import numpy as np
import json
import joblib
import tensorflow as tf
from tensorflow.keras.models import load_model
import mediapipe as mp

# CONFIG
VIDEO_PATH = "app/videos/afternoon/afternoon_1.mp4"  # Eğitimde kullanılan bir video
MODEL_PATH = "app/model/sign_language_recognition.keras"
LABEL_ENCODER_PATH = "app/model/label_encoder.pkl"
FEATURE_ORDER_PATH = "app/model/feature_order.json"
SCALER_PATH = "app/model/scaler.pkl"
SEQUENCE_LENGTH = 5
FPS = 15
WINDOW_SEC = 0.5

# Load model and tools
model = load_model(MODEL_PATH)
le = joblib.load(LABEL_ENCODER_PATH)
scaler = joblib.load(SCALER_PATH)
with open(FEATURE_ORDER_PATH) as f:
    feature_order = json.load(f)

# Initialize MediaPipe
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(static_image_mode=False)


# Landmark extraction from video file
def extract_landmarks_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_idx = 1
    all_landmarks = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        frame_landmarks = []

        def append_lms(lms, lm_type, hand=None):
            if lms:
                for idx, lm in enumerate(lms.landmark):
                    frame_landmarks.append(
                        {
                            "frame": frame_idx,
                            "type": lm_type,
                            "hand": hand,
                            "lm_id": idx,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                        }
                    )

        append_lms(results.left_hand_landmarks, "hand", hand=0)
        append_lms(results.right_hand_landmarks, "hand", hand=1)
        append_lms(results.pose_landmarks, "pose")

        if len(frame_landmarks) >= 50:
            all_landmarks.extend(frame_landmarks)

        frame_idx += 1

    cap.release()
    return pd.DataFrame(all_landmarks)


# Feature extraction
def extract_window_features(df, fps=15, window_sec=0.5):
    from app.utils.feature_extraction import extract_window_features

    return extract_window_features(df, fps, window_sec)


# Prepare input for LSTM
def prepare_input(wdf, seq_len):
    wdf = wdf.sort_values("start_frame")
    if "video_id" not in wdf.columns:
        wdf["video_id"] = "test_video"

    X = wdf[feature_order].to_numpy(dtype=np.float32)
    X = scaler.transform(X)

    if X.shape[0] < seq_len:
        pad_len = seq_len - X.shape[0]
        X = np.pad(X, ((0, pad_len), (0, 0)), mode="constant")

    return X[:seq_len][np.newaxis, :, :]


# Prediction pipeline (video dosyasından)
def predict_from_video():
    df = extract_landmarks_from_video(VIDEO_PATH)
    if df.empty:
        print("No landmarks detected.")
        return

    window_df = extract_window_features(df, fps=FPS, window_sec=WINDOW_SEC)
    X = prepare_input(window_df, SEQUENCE_LENGTH)
    pred = model.predict(X)[0]

    class_idx = np.argmax(pred)
    label = le.inverse_transform([class_idx])[0]

    print(f"\nPredicted label: {label} (Confidence: {pred[class_idx]:.2f})")
    for i, p in enumerate(pred):
        print(f"{le.inverse_transform([i])[0]:10}: {p:.2f}")


# Prediction pipeline (gerçek zamanlı)
def predict_from_realtime():
    print("Starting webcam capture. Please sign...")
    cap = cv2.VideoCapture(2)
    frame_idx = 1
    all_landmarks = []
    max_frames = FPS * 3

    while frame_idx <= max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        results = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        frame_landmarks = []

        def append_lms(lms, lm_type, hand=None):
            if lms:
                for idx, lm in enumerate(lms.landmark):
                    frame_landmarks.append(
                        {
                            "frame": frame_idx,
                            "type": lm_type,
                            "hand": hand,
                            "lm_id": idx,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                        }
                    )

        append_lms(results.left_hand_landmarks, "hand", hand=0)
        append_lms(results.right_hand_landmarks, "hand", hand=1)
        append_lms(results.pose_landmarks, "pose")

        if len(frame_landmarks) >= 50:
            all_landmarks.extend(frame_landmarks)

        frame_idx += 1

    cap.release()

    df = pd.DataFrame(all_landmarks)
    if df.empty:
        print("No landmarks detected.")
        return

    window_df = extract_window_features(df, fps=FPS, window_sec=WINDOW_SEC)
    X = prepare_input(window_df, SEQUENCE_LENGTH)
    pred = model.predict(X)[0]

    class_idx = np.argmax(pred)
    label = le.inverse_transform([class_idx])[0]

    print(f"\n[REALTIME] Predicted label: {label} (Confidence: {pred[class_idx]:.2f})")
    for i, p in enumerate(pred):
        print(f"{le.inverse_transform([i])[0]:10}: {p:.2f}")


if __name__ == "__main__":
    predict_from_video()
    # predict_from_realtime()  # Uncomment to test realtime prediction
