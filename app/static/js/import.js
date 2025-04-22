// import.js
$(document).ready(function() {
    $('#importForm').on('submit', function(e) {
      e.preventDefault();
      const label = $('#import_label').val().trim();
      const fileInput = document.getElementById('videoFile');
      if (!label || !fileInput.files.length) {
        $('#alert-area').html(
          '<div class="alert alert-warning">Label and video file are required.</div>'
        );
        return;
      }
      const formData = new FormData();
      formData.append('label', label);
      formData.append('video', fileInput.files[0]);
      formData.append('mirror', $('#mirrorSwitch').is(':checked'));
  
      fetch('/import', {
        method: 'POST',
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          $('#alert-area').html(
            '<div class="alert alert-success">Import started.</div>'
          );
          // Progress bar göster
          $('#progressContainer').show();
          console.log('Import started. Task ID:', data.task_id);
          startLandmarkExtraction(data.task_id);
        } else {
          $('#alert-area').html(
            '<div class="alert alert-danger">' + data.message + '</div>'
          );
        }
      })
      .catch(err => {
        console.error(err);
        $('#alert-area').html(
          '<div class="alert alert-danger">An error occurred.</div>'
        );
      });
    });
  });