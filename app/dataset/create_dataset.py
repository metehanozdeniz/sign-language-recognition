import cv2 as cv
import mediapipe as mp
import copy
import app.shared as shared  # Bu yöntemle shared modülünün içeriğine erişip güncelleme yapabilirsin.

from app.utils import (
    CvFpsCalc,
    calc_landmark_list,
    pre_process_landmark,
    draw_landmarks,
    draw_info_text,
    draw_info,
)

# Global camera instance and settings:
cap_device = 0
cap_width = 640
cap_height = 480
# Kamera global olarak sadece bir kere açılıyor:
cap = cv.VideoCapture(cap_device)
cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)


def gen_frames():
    global shared  # shared modülünü kullanıyoruz

    max_num_hands = 2
    min_detection_confidence = 0.5
    min_tracking_confidence = 0.5
    model_complexity = 1
    use_static_image_mode = False

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=max_num_hands,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
        model_complexity=model_complexity,
    )

    calculate_fps = CvFpsCalc(buffer_len=10)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        fps = calculate_fps.get()
        debug_image = copy.deepcopy(frame)
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        frame.flags.writeable = False
        results = hands.process(frame)
        frame.flags.writeable = True

        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)
                pre_processed = pre_process_landmark(landmark_list)
                # Ortak shared modülündeki global değişkeni güncellenmesi:
                shared.last_landmark = pre_processed

                debug_image = draw_landmarks(debug_image, landmark_list)

        debug_image = draw_info(debug_image, fps)
        ret2, buffer_img = cv.imencode(".jpg", debug_image)
        if not ret2:
            break
        frame_bytes = buffer_img.tobytes()

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    cap.release()
    cv.destroyAllWindows()
