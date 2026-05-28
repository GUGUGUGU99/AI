function formatText(command) {
  document.execCommand(command, false, null);
}

function applyFontSize() {
  const size = document.getElementById("fontSizeInput").value;
  const selection = window.getSelection();

  if (!selection.rangeCount) return;

  const range = selection.getRangeAt(0);

  if (range.collapsed) {
    document.getElementById("editor").style.fontSize = size + "px";
    return;
  }

  const span = document.createElement("span");
  span.style.fontSize = size + "px";

  range.surroundContents(span);
  selection.removeAllRanges();
}

function saveEditorContent() {
  const editor = document.getElementById("editor");
  const content = document.getElementById("content");
  content.value = editor.innerHTML;
}

function insertImage() {
  const imageInput = document.getElementById("imageInput");
  imageInput.value = "";
  imageInput.click();
}

document.addEventListener("DOMContentLoaded", function () {
  const imageInput = document.getElementById("imageInput");

  imageInput.addEventListener("change", function () {
    const file = imageInput.files[0];

    if (!file) return;

    const reader = new FileReader();

    reader.onload = function (e) {
      const editor = document.getElementById("editor");

      const img = document.createElement("img");
      img.src = e.target.result;
      img.className = "editor-image";
      img.style.width = "500px";
      img.style.maxWidth = "100%";
      img.style.display = "block";
      img.style.margin = "15px 0";

      editor.appendChild(img);
      editor.focus();
    };

    reader.readAsDataURL(file);
  });
});