import os
import cv2
import mediapipe as mp

from app import celery, db
from app.models import Video, FrameLandmark  # DB Models
from app.utils.feature_extraction import save_video_features


@celery.task(bind=True)
def process_video_landmarks(self, video_id, mirror=True, start_time=0.0, end_time=None):
    """
    video_id ile Video kaydını bulur, path üzerinden kare kare landmark çıkarır.
    Orijinal ve isteğe bağlı "mirror" (aynalanmış) veriyi işler.
    Her landmark'ı FrameLandmark tablosuna yazar, update_state ile ilerleme bildirir.
    """

    # get video and path
    video = Video.query.get(video_id)
    if not video or not os.path.exists(video.path):
        return {"status": "error", "message": "Video not found on disk."}

    # Video duration ve frame count
    cap = cv2.VideoCapture(video.path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # default fps
    desired_fps = 15.0
    frame_skip = max(1, round(fps / desired_fps))  # frame skip rate

    # Total frame count
    raw_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    # frame count
    try:
        total_frames = int(raw_count)
        if total_frames <= 0 or total_frames > 100000:
            raise ValueError
    except:
        # Fallback: manually count frames
        total_frames = 0
        while cap.read()[0]:
            ret, _ = cap.read()
            if not ret:
                break
            total_frames += 1
        cap.release()
        cap = cv2.VideoCapture(video.path)

    # Calculate the duration and save it to the DB
    duration = total_frames / fps if fps > 0 else 0
    video.duration = float(duration)
    db.session.commit()

    # Set start_time and end_time
    if start_time < 0:
        start_time = 0
    if end_time is not None and end_time < 0:
        end_time = 0
    if end_time is not None and end_time > duration:
        end_time = duration
    if end_time is None:
        end_time = duration
    if start_time >= end_time:
        return {
            "status": "error",
            "message": "Start time must be less than end time.",
        }
    if start_time == end_time:
        return {
            "status": "error",
            "message": "Start time and end time must be different.",
        }
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps) if end_time else total_frames
    end_frame = min(end_frame, total_frames)

    # Determine total work steps
    window_duration = (end_frame - start_frame) / fps
    # Each frame is skipped one step, mirror=True is double the steps.
    processed_frames = int(window_duration * desired_fps)
    # If mirror is enabled, double the steps
    total_steps = processed_frames * (2 if mirror else 1)
    step = 0

    # MediaPipe setup
    mp_hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    mp_pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    current_frame = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        current_frame += 1

        """
        Jump frame :
        jump as much as frame_skip in each current_frame
        This option can be left to the user's discretion.
        If the user wants to process every frame, set frame_skip to 1.
        """
        if current_frame % frame_skip != 0:
            continue
        if current_frame < start_frame or current_frame > end_frame:
            continue

        # ===== Process original frame =====
        step += 1
        # Report progress
        self.update_state(
            state="PROGRESS", meta={"current": step, "total": total_steps}
        )

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands_res = mp_hands.process(frame_rgb)
        pose_res = mp_pose.process(frame_rgb)

        # Hand landmarks
        if hands_res.multi_hand_landmarks:
            for hand_idx, hand_lms in enumerate(hands_res.multi_hand_landmarks):
                for lm_idx, lm in enumerate(hand_lms.landmark):
                    db.session.add(
                        FrameLandmark(
                            video_id=video.id,
                            frame_index=current_frame,
                            hand=hand_idx,
                            landmark_id=lm_idx,
                            x=float(lm.x),
                            y=float(lm.y),
                            z=float(lm.z),
                            type="hand",
                        )
                    )

        # Pose landmarks [0 - 22]
        if pose_res.pose_landmarks:
            for lm_idx, lm in enumerate(pose_res.pose_landmarks.landmark[:23]):
                db.session.add(
                    FrameLandmark(
                        video_id=video.id,
                        frame_index=current_frame,
                        hand=-1,
                        landmark_id=lm_idx,
                        x=float(lm.x),
                        y=float(lm.y),
                        z=float(lm.z),
                        type="pose",
                    )
                )

        # ===== Process mirror frame =====
        if mirror:
            # Mirrrored frame
            mf = cv2.flip(frame, 1)
            mf_rgb = cv2.cvtColor(mf, cv2.COLOR_BGR2RGB)
            hands_mir = mp_hands.process(mf_rgb)
            pose_mir = mp_pose.process(mf_rgb)

            step += 1
            # Report progress
            self.update_state(
                state="PROGRESS", meta={"current": step, "total": total_steps}
            )

            # Hand Landmarks
            if hands_mir.multi_hand_landmarks:
                for hand_idx, hand_lms in enumerate(hands_mir.multi_hand_landmarks):
                    for lm_idx, lm in enumerate(hand_lms.landmark):
                        db.session.add(
                            FrameLandmark(
                                video_id=video.id,
                                frame_index=current_frame,
                                hand=1 - hand_idx,
                                landmark_id=lm_idx,
                                x=1.0 - float(lm.x),
                                y=float(lm.y),
                                z=float(lm.z),
                                type="hand",
                            )
                        )

            # Pose Landmarks [0 - 22]
            if pose_mir.pose_landmarks:
                for lm_idx, lm in enumerate(pose_mir.pose_landmarks.landmark[:23]):
                    db.session.add(
                        FrameLandmark(
                            video_id=video.id,
                            frame_index=current_frame,
                            hand=-1,
                            landmark_id=lm_idx,
                            x=1.0 - float(lm.x),
                            y=float(lm.y),
                            z=float(lm.z),
                            type="pose",
                        )
                    )

        # commit per 50 frames
        # to avoid memory issues
        if current_frame % 50 == 0:
            db.session.commit()

    # Commit last batch
    db.session.commit()
    cap.release()
    mp_hands.close()
    mp_pose.close()

    # Feature extraction
    feature_count = save_video_features(video_id, fps=desired_fps, window_sec=0.5)

    return {
        "status": "success",
        "message": f"Landmarks & {feature_count} feature windows extracted.",
        "current": step,
        "total": total_steps,
        "feature_count": feature_count,
    }
