FROM tensorflow/tensorflow:2.15.0-gpu

WORKDIR /app

# System Dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY . .

# Environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=development

CMD ["flask", "run", "--host=0.0.0.0"]