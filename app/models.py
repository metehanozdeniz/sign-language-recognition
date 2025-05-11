from datetime import datetime
from app import db


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
    start_frame = db.Column(db.Integer, nullable=True)
    end_frame = db.Column(db.Integer, nullable=True)

    video = db.relationship("Video", back_populates="features")
