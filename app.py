import cv2 as cv
import mediapipe as mp
from collections import (
    deque,
)  # deque is a list-like container with fast appends and pops on either end
import copy  # copy module provides generic shallow and deep copy operations

from utils import CvFpsCalc
from utils import calc_bounding_rect
from utils import calc_landmark_list
from utils import pre_process_landmark


def main():
    cap_device = 0  # 0 for webcam, 1 for external webcam, 2 for external webcam
    cap_width = 1920  # width of the frames
    cap_height = 1080  # height of the frames

    max_num_hands = 2  # maximum number of hands to detect
    min_detection_confidence = 0.5
    min_tracking_confidence = 0.5
    model_complexity = 1  # 0: lite, 1: full
    use_static_image_mode = False  # False: video stream, True: static image

    use_brect = True  # bounding rect use

    ################################################## Camera preparation #################################################
    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, cap_width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, cap_height)

    ############################################ Model load and initializations ############################################
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=max_num_hands,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
        model_complexity=model_complexity,
    )

    ###################################################### calculate FPS ####################################################
    calculate_fps = CvFpsCalc(buffer_len=10)

    ####################################### Coordinate History with queque datastructure ####################################
    history_length = 16
    point_history = deque(maxlen=history_length)

    while True:
        fps = calculate_fps.get()

        # Process Key (ESC: end)
        key = cv.waitKey(10)
        if key == 27:  # ESC
            break

        ############################################## Read frame ##########################################################
        ret, frame = cap.read()
        if not ret:
            break

        # image = cv.flip(image, 1)  # Mirror display

        debug_image = copy.deepcopy(frame)  # deepcopy for other process

        # BGR -> RGB
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        frame.flags.writable = False
        results = hands.process(frame)
        frame.flags.writable = True

        # Rendering results
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                print(hand_landmarks)

                # Bounding Box Calculation
                brect = calc_bounding_rect(debug_image, hand_landmarks)

                # Landmark calculation
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)
                print(landmark_list)  # Koordinatları ekrana yazdır

                # Conversion to relative coordinates / normalized coordinates
                pre_processed_landmark_list = pre_process_landmark(landmark_list)
