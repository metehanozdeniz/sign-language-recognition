let mediaRecorder, recordedChunks = [], stream, videoId, progressInterval, options = { mimeType: 'video/webm;codecs=vp9' };

const startBtn = document.getElementById('startRecordingBtn');
const stopBtn = document.getElementById('stopRecordingBtn');
const extractBtn = document.getElementById('extractBtn');
const preview = document.getElementById('preview');
const previewVideo = document.getElementById('previewVideo');
const progressContainer = document.getElementById('progressContainer');

// Once the page loads, access the camera and start the preview.
window.addEventListener('load', async () => {
  try {
    // if url contains "import" then do not access camera
    if (window.location.href.includes("record")) {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      preview.srcObject = stream;
      preview.play();
    }
  } catch (error) { // Control camera access error
    showAlert('danger', 'Camera access error: ' + error.message);
    console.error("Camera access error.", error);
  }
});

// "Start Recording" button click event
startBtn.addEventListener('click', () => {
  // If the mediaRecorder is already recording, do nothing
  if (mediaRecorder && mediaRecorder.state === "recording") return;

  recordedChunks = [];

  if (!stream) {
    showAlert('warning', "Camera stream is not available.");
    return;
  }

  ensureMimeType();


  try {
    mediaRecorder = new MediaRecorder(stream, options);
  } catch (e) {
    showAlert('danger', "MediaRecorder initialization failed: " + e.message);
    console.error("MediaRecorder initialization failed:", e);
    return;
  }

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data);
  };

  mediaRecorder.onstop = uploadVideo;

  mediaRecorder.start();

  // Add border style to the preview element
  preview.classList.add('recording-preview');
  toggleButtons(true);
});

// "Stop Recording" button click event
stopBtn.addEventListener('click', () => {
  // If the mediaRecorder is not recording, do nothing
  if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();

  // Reset border style
  preview.classList.remove('recording-preview');
  toggleButtons(false);
});

function uploadVideo() {
  const blob = new Blob(recordedChunks, { type: 'video/mp4' });
  const formData = new FormData();
  const label = document.getElementById('labelInput').value.trim();

  if (!label) return showAlert('warning', 'Label cannot be empty.');

  formData.append('label', label);
  formData.append('video', blob, 'video.webm');

  fetch('/save_video', { method:'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      console.log("SAVE_VIDEO RESPONSE:", data);

      if (data.status === 'success') {
        videoId = data.video_id;
        

        showPreviewModal(data.path);
      } else {
        showAlert('danger', data.message);
      }
    })
    .catch(err => showAlert('danger', 'Upload error: ' + err));
}

function showPreviewModal(videoUrl) {
  const modalVideo = document.getElementById('modalVideo');
  const startIn = document.getElementById('modalStartTime');
  const endIn = document.getElementById('modalEndTime');

  // video src & metadata
  modalVideo.src = videoUrl;
  modalVideo.load();
  modalVideo.onloadedmetadata = () => {
    const dur = modalVideo.duration.toFixed(1);
    startIn.value = 0;
    startIn.max = dur;
    endIn.value = dur;
    endIn.max = dur;

    // Open modal
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    modal.show();
  };
}

// Click event for the modal "Extract" button
document.getElementById('modalExtractBtn').addEventListener('click', () => {
  const start  = parseFloat(document.getElementById('modalStartTime').value);
  const end    = parseFloat(document.getElementById('modalEndTime').value);
  const mirror = document.getElementById('modalMirrorSwitch').checked;

  if (start >= end || isNaN(start) || isNaN(end)) {
    return showAlert('warning', 'Lütfen geçerli bir başlangıç ve bitiş zamanı girin.');
  }

  // kapat modal
  const modalEl = document.getElementById('previewModal');
  bootstrap.Modal.getInstance(modalEl).hide();

  // Çağır extraction
  extractSegment(start, end, mirror);
});

function extractSegment(start, end, mirror) {
  const fd = new FormData();
  fd.append('video_id', videoId);
  fd.append('mirror', mirror);
  fd.append('start_time', start);
  fd.append('end_time', end);

  fetch('/process_video', { method:'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (d.status==='success') {
        showAlert('success', d.message);
        startLandmarkExtraction(d.task_id);
      } else {
        showAlert('danger', d.message);
      }
    })
    .catch(err => showAlert('danger', 'Extraction error: ' + err));
}

function handleVideoSaved(data) {
  if (data.status === "success") {
    videoId = data.video_id;
    setupPreviewVideo(data.path);
    showAlert('success', 'Video saved successfully.');
  } else {
    showAlert('danger', data.message || 'Video saving failed.');
  }
}

function setupPreviewVideo(videoPath) {
  console.log("SAVE_VIDEO RESPONSE:", videoPath);
  previewVideo.src = videoPath;
  previewVideo.load();
  previewVideo.onloadedmetadata = () => {
    document.getElementById('startTime').value = 0;
    document.getElementById('endTime').value = previewVideo.duration.toFixed(1);
    showExtractionUI();
  }
}

function startLandmarkExtraction(taskId) {
  progressContainer.style.display = 'block';

  const interval = setInterval(() => {
    fetch(`/task_status/${taskId}`)
      .then(res => res.json())
      .then(data => {
        
        console.log("TASK STATUS:", data);

        if (data.total > 0) updateProgressBar((data.current / data.total) * 100);
        if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
          clearInterval(interval);
          progressContainer.style.display = 'none';
          showAlert('success', `Landmark extraction ${data.state.toLowerCase()}.`);
        }
      })
      .catch(err => {
        clearInterval(interval);
        console.error(err);
        showAlert('danger', 'Status check failed.');
      });
  }, 2000);
}

function updateProgressBar(percent) {
  const bar = document.getElementById('progressBar');
  bar.style.width = percent + '%';
  bar.textContent = Math.round(percent) + '%';
}

function toggleButtons(isRecording) {
  startBtn.disabled = isRecording;
  stopBtn.disabled = !isRecording;
}

function showExtractionUI() {
  previewVideo.style.display = 'block';
  document.getElementById('startTimeContainer').style.display = 'block';
  document.getElementById('endTimeContainer').style.display = 'block';
  document.getElementById('mirrorSwitchContainer').style.display = 'block';
  extractBtn.style.display = 'block';
  previewVideo.controls = true;
}

function showAlert(type, message) {
  document.getElementById('alert-area').innerHTML = 
    `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>`;
}

function ensureMimeType() {
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    options = { mimeType: 'video/webm;codecs=vp8' };
  }
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    options = { mimeType: 'video/webm' };
  }
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    showAlert('danger', "Your browser doesn't support recording video properly.");
    throw new Error("No supported MediaRecorder formats.");
  }
}
