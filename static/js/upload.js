
const form = document.getElementById("resumeForm");
const fileInput = document.getElementById("resume");
const fileName = document.getElementById("fileName");
const errorMessage = document.getElementById("errorMessage");
const submitButton = document.getElementById("submitButton");
const loadingMessage = document.getElementById("loadingMessage");

const MAX_FILE_SIZE = 5 * 1024 * 1024;

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
}

function clearError() {
    errorMessage.textContent = "";
    errorMessage.hidden = true;
}

function validateFile(file) {
    if (!file) {
        return "Please select a PDF resume.";
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        return "Only PDF resumes are supported.";
    }

    if (file.size === 0) {
        return "Your selected file is empty.";
    }

    if (file.size > MAX_FILE_SIZE) {
        return "Your PDF must be 5 MB or smaller.";
    }

    return null;
}

fileInput.addEventListener("change", () => {
    clearError();

    const file = fileInput.files[0];

    if (!file) {
        fileName.textContent = "";
        return;
    }

    const error = validateFile(file);

    if (error) {
        showError(error);
        fileName.textContent = "";
    } else {
        fileName.textContent = `Selected: ${file.name}`;
    }
});

form.addEventListener("submit", (event) => {
    clearError();

    const error = validateFile(fileInput.files[0]);

    if (error) {
        event.preventDefault();
        showError(error);
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "PROCESSING...";
    loadingMessage.hidden = false;
});
