// ==========================================================================
// MARKS ANALYSER — DESKTOP LAUNCHER UPLOADER
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Window Controls on Launch Screen
  const minBtn = document.getElementById('winMinBtn');
  const maxBtn = document.getElementById('winMaxBtn');
  const closeBtn = document.getElementById('winCloseBtn');

  if (minBtn) {
    minBtn.onclick = () => {
      document.body.style.opacity = '0.4';
      setTimeout(() => { document.body.style.opacity = '1'; }, 600);
    };
  }

  if (maxBtn) {
    maxBtn.onclick = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
        maxBtn.textContent = '❐';
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        }
        maxBtn.textContent = '□';
      }
    };
  }

  if (closeBtn) {
    closeBtn.onclick = () => {
      if (confirm('Exit Marks Analyser?')) {
        window.close();
      }
    };
  }

  // Upload Form Handlers
  const uploadForm = document.getElementById('uploadForm');
  if (!uploadForm) return;

  const fileInput = document.getElementById('pdfFile');
  const dropZone = document.getElementById('dropZone');
  const choosePdf = document.getElementById('choosePdf');
  const meta = document.getElementById('fileMeta');
  const errorBox = document.getElementById('uploadError');
  const button = document.getElementById('analyzeButton');

  const showFile = (file) => {
    if (!file) return;
    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    if (!isPdf || !file.size) {
      errorBox.textContent = 'Invalid file. Please select a valid, non-empty university result PDF.';
      button.disabled = true;
      return;
    }
    errorBox.textContent = '';
    meta.innerHTML = `<b>${file.name}</b> · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    button.disabled = false;
  };

  if (choosePdf && fileInput) {
    choosePdf.onclick = (e) => {
      e.stopPropagation();
      fileInput.click();
    };
  }

  if (dropZone && fileInput) {
    dropZone.onclick = () => fileInput.click();

    fileInput.onchange = () => showFile(fileInput.files[0]);

    ['dragenter', 'dragover'].forEach(event => {
      dropZone.addEventListener(event, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragging');
      });
    });

    ['dragleave', 'drop'].forEach(event => {
      dropZone.addEventListener(event, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragging');
      });
    });

    dropZone.ondrop = (e) => {
      const file = e.dataTransfer.files[0];
      if (file) {
        fileInput.files = e.dataTransfer.files;
        showFile(file);
      }
    };
  }

  uploadForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return;

    button.disabled = true;
    button.innerHTML = '<span>Analyzing Result Ledger...</span> <span class="spinner"></span>';
    errorBox.textContent = '';

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: new FormData(uploadForm)
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || 'Unable to parse this PDF result file.');
      }
      window.location.reload();
    } catch (err) {
      errorBox.textContent = err.message;
      button.disabled = false;
      button.innerHTML = '<span>Run Marks Analyser</span> <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
    }
  };
});
