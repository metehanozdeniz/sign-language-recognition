import numpy as np
import pandas as pd
from app import db
from app.models import FrameLandmark, VideoFeature


def load_landmarks_df(video_id):
    """FrameLandmark tablosundan pandas DataFrame’e çevir."""
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
    DataFrame’deki tüm landmark’ları, sabit süreli pencerelere böler
    ve her pencere için özet istatistikler üretir.
    """
    window_size = int(fps * window_sec)
    features = []
    finger_tips = [4, 8, 12, 16, 20]  # 4, 8, 12, 16, 20:el parmak uçları
    pose_joints = [
        11,
        12,
        13,
        14,
        15,
        16,
    ]  # 11, 12, 13, 14, 15, 16: omuz, dirsek, bilek

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

        # El parmak uçları: mean/std
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

        # Pose omuz/kalça
        joints = w[(w.type == "pose") & (w.lm_id.isin(pose_joints))]
        for ax in ("x", "y", "z"):
            feat[f"joints_{ax}_mean"] = float(joints[ax].mean())
            feat[f"joints_{ax}_std"] = float(joints[ax].std())

        features.append(feat)

    return pd.DataFrame(features)


def save_video_features(video_id, fps=15, window_sec=0.5):
    """
    load_landmarks_df → extract_window_features → VideoFeature tablosuna kaydet
    """
    df = load_landmarks_df(video_id)
    if df.empty:
        return 0
    # Ekstra: df['video'] sütunu yoksa ekleyin:
    df["video"] = video_id
    wdf = extract_window_features(df, fps, window_sec)

    # Tabloya yaz
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
