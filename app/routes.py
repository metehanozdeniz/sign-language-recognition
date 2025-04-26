import os
from datetime import datetime

from flask import (
    render_template,
    Response,
    request,
    jsonify,
    send_from_directory,
    url_for,
)
from celery.result import AsyncResult

import app.shared as shared  # shared modülünden global değişkene erişim sağlıyoruz.
from app import app, db
from app.dataset.create_dataset import gen_frames
from app.utils.database_insertion import insert_landmark_record
from app.models import Dataset, Video  # DB Models
from app.tasks import process_video_landmarks, celery
from app.config import VIDEO_DIR


@app.route("/")
def index():
    return render_template("index.html")


# --- Helper for saving videos to DB and filesystem ---
def _save_video_file(label, video_file):
    """
    Saves uploaded video to disk and creates a Video record in the database.
    Returns the Video instance.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(VIDEO_DIR, label)
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{timestamp}.webm"
    video_path = os.path.join(save_dir, filename)
    video_file.save(video_path)

    video = Video(path=video_path, label=label)
    db.session.add(video)
    db.session.commit()
    return video


@app.route("/create-dataset", methods=["GET", "POST"])
def create_dataset():
    if request.method == "POST":
        label = request.form.get("dataset_label", "").strip()
        if label == "":
            # print("POST alındı, label boş.") # Debug
            return jsonify({"status": "error", "message": "Label can not be empty."})
        # print("POST alındı, label:", label)  # Debug
        if shared.last_landmark is None:
            print("shared.last_landmark None, DB'ye yazılmadı.")
            return jsonify(
                {
                    "status": "error",
                    "message": "No data to save. Please try again.",
                }
            )
        if len(shared.last_landmark) != 42:
            print("shared.last_landmark 42 değil, DB'ye yazılmadı.")
            return jsonify(
                {"status": "error", "message": "Landmark data is incomplete."}
            )

        try:
            insert_landmark_record(label, shared.last_landmark)
        except exec as e:
            return jsonify({"status": "error", "message": str(e)})

        # logging_csv(label, shared.last_landmark)
        return jsonify({"status": "success"})

    # GET isteğinde normal şekilde render et
    return render_template("create_dataset.html")


@app.route("/get_db_data", methods=["GET"])
def get_db_data():
    records = Dataset.query.all()
    data = []
    for record in records:
        row = [getattr(record, f"landmark_{i}") for i in range(42)]
        row.insert(0, record.label)
        data.append(row)
    return jsonify(data)


@app.route("/record", methods=["GET"])
def record_page():
    video_list = []
    # videos klasörünün mutlak yolunu oluşturuyoruz
    base_path = os.path.join(app.root_path, "videos")

    if os.path.exists(base_path):
        # Her alt klasör, bir kelime etiketini temsil eder.
        for label in os.listdir(base_path):
            label_path = os.path.join(base_path, label)
            if os.path.isdir(label_path):
                for video_file in os.listdir(label_path):
                    # Video yolunu, videoyu sunacak route'dan erişilebilecek şekilde oluşturuyoruz.
                    relative_path = os.path.join(label, video_file)
                    video_list.append(
                        {
                            "label": label,
                            "filename": video_file,
                            "url": url_for("serve_video", filename=relative_path),
                        }
                    )
    return render_template("save_video.html", videos=video_list)


@app.route("/import", methods=["GET"])
def import_page():
    return render_template("import.html")


@app.route("/import", methods=["POST"])
def import_video():
    """
    Handles external video upload and kicks off landmark+feature extraction.
    """
    label = request.form.get("label", "").strip()
    if not label:
        return jsonify({"status": "error", "message": "Label is required."}), 400

    video_file = request.files.get("video")
    if not video_file:
        return jsonify({"status": "error", "message": "No video file uploaded."}), 400

    # reuse helper to save file & DB record
    video = _save_video_file(label, video_file)

    # video path
    rel_path = os.path.relpath(video.path, os.path.join(app.root_path, "videos"))
    video_url = url_for("serve_video", filename=rel_path)

    # mirror setting
    mirror = request.form.get("mirror", "true").lower() == "true"
    task = process_video_landmarks.apply_async(
        args=[video.id], kwargs={"mirror": mirror}
    )

    return jsonify(
        {
            "status": "success",
            "message": "Import started.",
            "video_id": video.id,
            "video_url": video_url,
            "task_id": task.id,
        }
    )


@app.route("/save_video", methods=["POST"])
def save_video():
    label = request.form.get("label", "").strip()
    if not label:
        return jsonify({"status": "error", "message": "Label can not be empty."}), 400

    video_file = request.files.get("video")
    if not video_file:
        return jsonify({"status": "error", "message": "No video uploaded."}), 400

    video = _save_video_file(label, video_file)

    rel_path = os.path.relpath(video.path, os.path.join(app.root_path, "videos"))
    video_url = url_for("serve_video", filename=rel_path)

    return jsonify(
        {
            "status": "success",
            "message": "Video saved successfully.",
            "video_id": video.id,
            "path": video_url,
        }
    )


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# for submission of video files
@app.route("/videos/<path:filename>")
def serve_video(filename):
    # 'videos' klasörünü uygulamanın root klasörü altında varsayılıyor
    return send_from_directory(os.path.join(app.root_path, "videos"), filename)


# for gallery
@app.route("/gallery", methods=["GET"])
def gallery():
    video_list = []
    # videos klasörünün mutlak yolunu oluşturuyoruz
    base_path = os.path.join(app.root_path, "videos")

    if os.path.exists(base_path):
        # Her alt klasör, bir kelime etiketini temsil eder.
        for label in os.listdir(base_path):
            label_path = os.path.join(base_path, label)
            if os.path.isdir(label_path):
                for video_file in os.listdir(label_path):
                    # Video yolunu, videoyu sunacak route'dan erişilebilecek şekilde oluşturuyoruz.
                    relative_path = os.path.join(label, video_file)
                    video_list.append(
                        {
                            "label": label,
                            "filename": video_file,
                            "url": url_for("serve_video", filename=relative_path),
                        }
                    )
    return render_template("gallery.html", videos=video_list)


@app.route("/process_video", methods=["POST"])
def process_video():
    """
    AJAX ile çağrılan endpoint: video_id alıp arka planda Celery task'ını başlatır.
    """
    video_id = request.form.get("video_id", type=int)
    # get mirror value from form (default: true)
    mirror = request.form.get("mirror", "true").lower() == "true"
    # get start_time and end_time from form
    start_time = request.form.get("start_time", type=float, default=0.0)
    end_time = request.form.get("end_time", type=float, default=0.0)

    if start_time >= end_time:
        return jsonify(
            {"status": "error", "message": "Start time must be less than end time."}
        ), 400
    if start_time < 0 or end_time < 0:
        return jsonify(
            {"status": "error", "message": "Start and end time must be positive."}
        ), 400
    if start_time == end_time:
        return jsonify(
            {"status": "error", "message": "Start time and end time must be different."}
        ), 400

    video = Video.query.get(video_id)
    if not video:
        return jsonify({"status": "error", "message": "Video not found."}), 404

    # start the Celery task and send video_id and mirror value
    # to the task
    task = process_video_landmarks.apply_async(
        args=[video_id],
        kwargs={
            "mirror": mirror,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    return jsonify(
        {
            "status": "success",
            "task_id": task.id,
            "message": "Landmark extraction started.",
        }
    )


@app.route("/task_status/<task_id>", methods=["GET"])
def task_status(task_id):
    task = AsyncResult(task_id, app=celery)

    if task.state == "PENDING":
        # Görev henüz başlatılmamış veya sonuç kaydı yok
        response = {
            "state": task.state,
            "current": 0,
            "total": 1,
            "status": "Pending...",
        }
    elif task.state == "PROGRESS":
        # PROGRESS durumunda, görev ilerleme verisi (current, total) içerir
        response = {
            "state": task.state,
            "current": task.info.get("current", 0),
            "total": task.info.get("total", 1),
            "status": task.info.get("status", ""),
        }
    elif task.state == "SUCCESS":
        response = {
            "state": task.state,
            "current": task.info.get("current", 0),
            "total": task.info.get("total", 1),
            "status": "Completed",
        }
    else:
        # FAILURE veya başka bir durum
        response = {
            "state": task.state,
            "current": 0,
            "total": 1,
            "status": str(task.info),
        }

    return jsonify(response)
