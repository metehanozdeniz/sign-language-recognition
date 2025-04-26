$(document).ready(function () {
  $('#importForm').on('submit', function (e) {
    e.preventDefault();
    const label = $('#import_label').val().trim();
    const fileInput = document.getElementById('videoFile');
    if (!label || !fileInput.files.length) {
      showAlert('warning', 'Please provide a label and select a video file.');
      return;
    }

    const formData = new FormData();
    formData.append('label', label);
    formData.append('video', fileInput.files[0]);

    fetch('/import', {
      method: 'POST',
      body: formData
    })
      .then(res => res.json())
      .then(data => {

        console.log('IMPORT RESPONSE:', data);
        window.importedVideoId = data.video_id;

        const modalVideo = document.getElementById('modalVideo');
        modalVideo.src = data.video_url;
        modalVideo.load();
        modalVideo.onloadedmetadata = () => {
          const dur = modalVideo.duration.toFixed(1);
          $('#startTime').val(0);
          $('#startTime').attr('max', dur);
          $('#endTime').val(dur);
          $('#endTime').attr('max', dur);

          // Open modal
          const modal = new bootstrap.Modal(document.getElementById('previewModal'));
          modal.show();
        }


      })
      .catch(err => {
        console.error(err);
        showAlert('danger', 'An error occurred while importing the video.');
      });
  });
});

//extraxt button
$('#modalExtractBtn').on('click', () => {
  const start = parseFloat($('#modalStartTime').val());
  const end = parseFloat($('#modalEndTime').val());
  const mirror = $('#modalMirrorSwitch').is(':checked');

  if (!window.importedVideoId) {
    showAlert('warning', 'No video selected. Please select a video to extract landmarks.');
    return;
  }

  if (start >= end || isNaN(start) || isNaN(end)) {
    showAlert('warning', 'Invalid time range. Please check the start and end times.');
    return;
  }
  // Close modal
  bootstrap.Modal.getInstance($('#previewModal')).hide();

  // start landmark extraction
  const fd = new FormData();
  fd.append('video_id', window.importedVideoId);
  fd.append('mirror', mirror);
  fd.append('start_time', start);
  fd.append('end_time', end);

  fetch('/process_video', { method: 'POST', body: fd })
    .then(res => res.json())
    .then(d => {
      if (d.status === 'success') {
        showAlert('success', d.message);
        startLandmarkExtraction(d.task_id);
      } else {
        showAlert('danger', d.message);
      }
    })
    .catch(err => {
      console.error(err);
      showAlert('danger', 'Extraction error: ' + err);
    });
});

function showAlert(type, msg) {
  $('#alert-area').html(`
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${msg}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  `);
}