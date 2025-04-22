import cv2
import mediapipe as mp


def draw_landmarks():
    cap = cv2.VideoCapture(2)

    # Mediapipe setup
    mp_drawing = mp.solutions.drawing_utils

    # Open video capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Set video properties
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    mp_holistic = mp.solutions.holistic

    with mp_holistic.Holistic(
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame.")
                break

            # Recolor feed
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Make detection
            results = holistic.process(frame_rgb)

            # Recolor image back to BGR
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # Draw landmarks
            mp_drawing.draw_landmarks(
                frame_bgr,
                results.pose_landmarks,
                mp_holistic.POSE_CONNECTIONS,
            )

            cv2.imshow("Pose Tracking", frame_bgr)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


draw_landmarks()
