import numpy as np
import pandas as pd
from app import db
from app.models import FrameLandmark, VideoFeature


def load_landmarks_df(video_id):
    """Convert FrameLandmark table to DataFrame."""
    records = (
        db.session.query(FrameLandmark)
        .filter_by(video_id=video_id)
        .order_by(FrameLandmark.frame_index)
        .all()
    )
    data = [
        {
            "frame": r.frame_index,
            "hand": r.hand,
            "lm_id": r.landmark_id,
            "x": r.x,
            "y": r.y,
            "z": r.z,
            "type": r.type,
        }
        for r in records
    ]
    return pd.DataFrame(data)


def extract_window_features(df, fps=15, window_sec=0.5):
    """
    It divides all landmarks in the DataFrame into fixed duration windows and produces summary statistics for each window.
    """
    window_size = int(fps * window_sec)
    features = []
    finger_tips = [4, 8, 12, 16, 20]  # 4, 8, 12, 16, 20:hand fingertips
    pose_joints = [
        11,
        12,
        13,
        14,
        15,
        16,
    ]  # 11, 12, 13, 14, 15, 16: shoulder, elbow, wrist

    max_frame = int(df["frame"].max())
    for start in range(1, max_frame + 1, window_size):
        end = start + window_size - 1
        w = df[(df.frame >= start) & (df.frame <= end)]
        if w.empty:
            continue

        feat = {
            "video_id": df["video"].iloc[0] if "video" in df else None,
            "start_frame": start,
            "end_frame": end,
        }

        # hand fingertips: mean/std
        for hand_side, hand_label in [(0, "left"), (1, "right")]:
            tips = w[
                (w.type == "hand") & (w.lm_id.isin(finger_tips)) & (w.hand == hand_side)
            ]
            for ax in ("x", "y", "z"):
                feat[f"{hand_label}_tips_{ax}_mean"] = (
                    float(tips[ax].mean()) if not tips.empty else 0.0
                )
                feat[f"{hand_label}_tips_{ax}_std"] = (
                    float(tips[ax].std()) if not tips.empty else 0.0
                )

        # Pose shoulder, elbow, wrist: mean/std
        joints = w[(w.type == "pose") & (w.lm_id.isin(pose_joints))]
        for ax in ("x", "y", "z"):
            feat[f"joints_{ax}_mean"] = float(joints[ax].mean())
            feat[f"joints_{ax}_std"] = float(joints[ax].std())

        features.append(feat)

    return pd.DataFrame(features)


def save_video_features(video_id, fps=15, window_sec=0.5):
    """
    load_landmarks_df → extract_window_features → save to db
    Deletes old existing VideoFeature recordings, then adds new ones.
    """
    try:
        VideoFeature.query.filter_by(video_id=video_id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()

    df = load_landmarks_df(video_id)
    if df.empty:
        return 0

    # Extra: Add video_id to DataFrame
    df["video"] = video_id
    wdf = extract_window_features(df, fps, window_sec)

    count = 0
    for _, row in wdf.iterrows():
        vid = int(row.pop("video_id"))
        # Her satırdaki tüm numeric öznitelikleri VideoFeature olarak ekleyin
        for key, val in row.items():
            # start_frame/end_frame özniteliğini atlayabiliriz
            if key in ("start_frame", "end_frame") or val is None or np.isnan(val):
                continue
            db.session.add(
                VideoFeature(video_id=vid, feature_name=key, value=float(val))
            )
        count += 1
    db.session.commit()
    return count
