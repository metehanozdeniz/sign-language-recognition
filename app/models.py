from datetime import datetime
from app import db


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False)
    # Landmarks columns
    landmark_0 = db.Column(db.Float, nullable=False)
    landmark_1 = db.Column(db.Float, nullable=False)
    landmark_2 = db.Column(db.Float, nullable=False)
    landmark_3 = db.Column(db.Float, nullable=False)
    landmark_4 = db.Column(db.Float, nullable=False)
    landmark_5 = db.Column(db.Float, nullable=False)
    landmark_6 = db.Column(db.Float, nullable=False)
    landmark_7 = db.Column(db.Float, nullable=False)
    landmark_8 = db.Column(db.Float, nullable=False)
    landmark_9 = db.Column(db.Float, nullable=False)
    landmark_10 = db.Column(db.Float, nullable=False)
    landmark_11 = db.Column(db.Float, nullable=False)
    landmark_12 = db.Column(db.Float, nullable=False)
    landmark_13 = db.Column(db.Float, nullable=False)
    landmark_14 = db.Column(db.Float, nullable=False)
    landmark_15 = db.Column(db.Float, nullable=False)
    landmark_16 = db.Column(db.Float, nullable=False)
    landmark_17 = db.Column(db.Float, nullable=False)
    landmark_18 = db.Column(db.Float, nullable=False)
    landmark_19 = db.Column(db.Float, nullable=False)
    landmark_20 = db.Column(db.Float, nullable=False)
    landmark_21 = db.Column(db.Float, nullable=False)
    landmark_22 = db.Column(db.Float, nullable=False)
    landmark_23 = db.Column(db.Float, nullable=False)
    landmark_24 = db.Column(db.Float, nullable=False)
    landmark_25 = db.Column(db.Float, nullable=False)
    landmark_26 = db.Column(db.Float, nullable=False)
    landmark_27 = db.Column(db.Float, nullable=False)
    landmark_28 = db.Column(db.Float, nullable=False)
    landmark_29 = db.Column(db.Float, nullable=False)
    landmark_30 = db.Column(db.Float, nullable=False)
    landmark_31 = db.Column(db.Float, nullable=False)
    landmark_32 = db.Column(db.Float, nullable=False)
    landmark_33 = db.Column(db.Float, nullable=False)
    landmark_34 = db.Column(db.Float, nullable=False)
    landmark_35 = db.Column(db.Float, nullable=False)
    landmark_36 = db.Column(db.Float, nullable=False)
    landmark_37 = db.Column(db.Float, nullable=False)
    landmark_38 = db.Column(db.Float, nullable=False)
    landmark_39 = db.Column(db.Float, nullable=False)
    landmark_40 = db.Column(db.Float, nullable=False)
    landmark_41 = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Dataset {self.label}>"


class Video(db.Model):
    __tablename__ = "video"
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Text, unique=True, nullable=False)
    label = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # relationships
    landmarks = db.relationship(
        "FrameLandmark", back_populates="video", cascade="all, delete-orphan"
    )
    features = db.relationship(
        "VideoFeature", back_populates="video", cascade="all, delete-orphan"
    )


class FrameLandmark(db.Model):
    __tablename__ = "frame_landmark"
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    frame_index = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "hand", "pose", etc.
    hand = db.Column(db.Integer, nullable=False)  # 0: left, 1: right, -1: pose
    landmark_id = db.Column(db.Integer, nullable=False)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    z = db.Column(db.Float, nullable=False)

    video = db.relationship("Video", back_populates="landmarks")


class VideoFeature(db.Model):
    __tablename__ = "video_feature"
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    feature_name = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float, nullable=False)

    video = db.relationship("Video", back_populates="features")
