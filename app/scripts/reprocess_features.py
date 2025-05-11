import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models import Video
from app.utils.feature_extraction import save_video_features

app = create_app()
with app.app_context():
    videos = Video.query.all()
    for video in videos:
        print(f"Processing video_id: {video.id}")
        save_video_features(video.id)
