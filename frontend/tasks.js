function connectPdfPicker(inputId, viewerId, statusId, expectedName) {
  const input = document.getElementById(inputId);
  const viewer = document.getElementById(viewerId);
  const status = document.getElementById(statusId);
  let objectUrl;

  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      status.textContent = 'Choose a PDF document.';
      input.value = '';
      return;
    }

    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
    objectUrl = URL.createObjectURL(file);
    viewer.src = objectUrl;
    viewer.classList.remove('is-hidden');
    status.textContent = `${file.name} is displayed locally. It is not uploaded.`;
  });

  window.addEventListener('pagehide', () => {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
  }, { once: true });

  input.setAttribute('aria-label', `Select ${expectedName}`);
}

function enableSurveyMousePractice() {
  const canvas = document.getElementById('survey-mouse-practice');
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('The browser could not initialize the survey mouse practice area.');
  }
  context.lineWidth = 3;
  context.lineCap = 'round';
  context.strokeStyle = '#1768d2';

  let drawing = false;
  function point(event) {
    const bounds = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - bounds.left) * canvas.width / bounds.width,
      y: (event.clientY - bounds.top) * canvas.height / bounds.height,
    };
  }

  canvas.addEventListener('pointerdown', (event) => {
    drawing = true;
    canvas.setPointerCapture(event.pointerId);
    const position = point(event);
    context.beginPath();
    context.moveTo(position.x, position.y);
    context.lineTo(position.x + 0.1, position.y + 0.1);
    context.stroke();
  });
  canvas.addEventListener('pointermove', (event) => {
    if (!drawing) {
      return;
    }
    const position = point(event);
    context.lineTo(position.x, position.y);
    context.stroke();
  });
  canvas.addEventListener('pointerup', () => {
    drawing = false;
  });
  canvas.addEventListener('pointercancel', () => {
    drawing = false;
  });
}

export function initializeTaskPages() {
  connectPdfPicker(
    'task0-pdf-input',
    'task0-pdf-viewer',
    'task0-pdf-status',
    'Transcription_scripts_Session0.pdf',
  );
  enableSurveyMousePractice();
}
