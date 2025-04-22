from app import db
from app.models import Dataset


def insert_landmark_record(label, landmarks):
    """
    label: String değer
    landmarks: 42 elemanlı (float) değer listesi.
    Eğer landmarks listesi 42 eleman içermiyorsa ValueError fırlatır.
    """
    if len(landmarks) != 42:
        raise ValueError("Landmark list must contain exactly 41 values.")

    # Modelin sütun isimlerine uygun olarak verileri dinamik oluşturulması.
    data = {"label": label}
    for i in range(42):
        data[f"landmark_{i}"] = landmarks[i]

    print("Data:", data)  # Debug

    new_record = Dataset(**data)
    db.session.add(new_record)
    db.session.commit()
