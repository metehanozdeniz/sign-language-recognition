let mediaRecorder;
let recordedChunks = [];
let stream;
const preview = document.getElementById('preview');
let progressInterval; // Celery görev ilerleme takibi için interval saklamak için
let options = { mimeType: 'video/webm;codecs=vp9' };

// Once the page loads, access the camera and start the preview.
window.addEventListener('load', async () => {
  try {
    // if url contains "import" then do not access camera
    if (window.location.href.includes("record")) {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      preview.srcObject = stream;
      preview.play();
    }
    else{
      console.log("This page does not require camera access.");
      return;
    }
  } catch (error) { // Control camera access error
    document.getElementById('alert-area').innerHTML = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
      'Camera access error - ' + error + ' Please check your permissions.' +
      '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
      '</div>';

    console.error("Camera access error.", error);
  }
});

// "Start Recording" button click event
document.getElementById('startRecordingBtn').addEventListener('click', () => {
  // If the mediaRecorder is already recording, do nothing
  if (mediaRecorder && mediaRecorder.state === "recording") return;

  recordedChunks = [];

  if (!stream) {
    alert("Camera stream is not available.");
    return;
  }


  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    options = { mimeType: 'video/webm;codecs=vp8' };
  }
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    options = { mimeType: 'video/webm' };
  }
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    alert("Tarayıcınız video kaydı için desteklenmeyen bir format kullanıyor.");
    throw new Error("Desteklenen bir MediaRecorder formatı bulunamadı.");
  }

  try {
    mediaRecorder = new MediaRecorder(stream, options);
  } catch (e) {
    console.error("MediaRecorder initialization failed:", e);
    alert("MediaRecorder is not supported in your browser.");
    return;
  }

  mediaRecorder.ondataavailable = function(event) {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };

  mediaRecorder.onstop = function () {
    const blob = new Blob(recordedChunks, { type: 'video/mp4' });
    const formData = new FormData();
    const label = document.getElementById('labelInput').value.trim();
    if (!label) {
      document.getElementById('alert-area').innerHTML = '<div class="alert alert-warning alert-dismissible fade show" role="alert">' +
        'Label can not be empty! Please enter a label for the video.' +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
        '</div>';

      // alert("Please enter a label for the video.");
      return;
    }
    formData.append('label', label);
    formData.append('video', blob, 'video.webm');

    fetch('/save_video', {
      method: 'POST',
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          // Display success message
          document.getElementById('alert-area').innerHTML = '<div class="alert alert-success alert-dismissible fade show" role="alert">' +
            'Video saved successfully.' +
            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
            '</div>';

          console.log('Video Saved:', data.path);

          // Start landmark extraction and follow the task status
          // send video_id for landmark extraction
          processVideoLandmarks(data.video_id);
        } else {
          document.getElementById('alert-area').innerHTML = 
            `<div class="alert alert-danger alert-dismissible fade show" role="alert">
               ${data.message || "Video saving failed."}
               <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
             </div>`;
        }
        // alert(data.message);
      })
      .catch(error => {
        document.getElementById('alert-area').innerHTML =
          document.getElementById('alert-area').innerHTML = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
          'Video submission error - ' + error + ' There  was an error submitting the video' +
          '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
          '</div>';

        console.error("Video submission error.", error);
      });

    // Reset border style
    preview.classList.remove('recording-preview');
  };

  mediaRecorder.start();

  // Add border style to the preview element
  preview.classList.add('recording-preview');

  // Update buttons
  document.getElementById('startRecordingBtn').disabled = true;
  document.getElementById('stopRecordingBtn').disabled = false;
});

// "Stop Recording" button click event
document.getElementById('stopRecordingBtn').addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }

  // Reset border style
  preview.classList.remove('recording');

  // Restore buttons
  document.getElementById('startRecordingBtn').disabled = false;
  document.getElementById('stopRecordingBtn').disabled = true;
});

// Function to process video landmarks
function processVideoLandmarks(videoId) {
  // Send the video path to the server for landmark extraction with POST request
  const formData = new FormData();
  formData.append('video_id', videoId);

  // Switch durumunu al
  const mirror = document.getElementById('mirrorSwitch').checked;
  formData.append('mirror', mirror);  // "true" veya "false"

  fetch('/process_video', {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success' && data.task_id) {
        document.getElementById('alert-area').innerHTML = '<div class="alert alert-success alert-dismissible fade show" role="alert">' +
          data.message +
          '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
          '</div>';
        //   alert(data.message);
        // İstersen landmark json dosyasının yolunu göster veya galeride işleyebilirsin.
        console.log(data.status);
        console.log(data.message);
        console.log("Task id: ", data.task_id);
        startLandmarkExtraction(data.task_id);
      } else {
        alert("Landmark extraction error: " + data.message);
      }
    })
    .catch(error => {
      console.error("Landmark extraction hatası:", error);
      alert("Landmark extraction sırasında hata oluştu.");
    });
}

// Celery task'ını takip eden fonksiyon: Belirli aralıklarla /task_status/<task_id>'i sorgular
function startLandmarkExtraction(taskId) {
  console.log("Landmark extraction task started with ID:", taskId);
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  if (progressContainer) {
    progressContainer.style.display = 'block';
  }

  // Her 2 saniyede bir durumu kontrol eden interval başlatılıyor.
  const interval = setInterval(() => {
    checkTaskStatus(taskId, interval);
  }, 2000);
}

// /task_status endpoint'inden gelen durumu sorgulayan fonksiyon
function checkTaskStatus(taskId, interval) {
  fetch(`/task_status/${taskId}`)
    .then(response => response.json())
    .then(data => {
      console.log("Task status: ", data);
      const progressBar = document.getElementById('progressBar');
      const progressContainer = document.getElementById('progressContainer');
      if (data.total > 0) {
        const percent = Math.round((data.current / data.total) * 100);

        if(progressBar) {
          progressBar.style.width = percent + '%';
          progressBar.textContent = percent + '%';
        }
      }
      if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
        clearInterval(interval);
        if(progressContainer) {
          progressContainer.style.display = 'none';
        }
        const message = data.state === 'SUCCESS' ? 'Landmark extraction completed successfully.' : 'Landmark extraction failed.';
        document.getElementById('alert-area').innerHTML =
          `<div class="alert alert-success alert-dismissible fade show" role="alert">
             ${message}
             <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
           </div>`;
        console.log(message);
      }
    })
    .catch(error => {
      clearInterval(interval);
      console.error("Task status error:", error);
      alert("Could not check task status.");
    });
}