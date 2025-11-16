const area = document.getElementById("uploadArea");
const input = document.getElementById("fileInput");

area.addEventListener("click", () => input.click());

input.addEventListener("change", () => upload(input.files[0]));

area.addEventListener("dragover", e => e.preventDefault());
area.addEventListener("drop", e => {
    e.preventDefault();
    upload(e.dataTransfer.files[0]);
});

async function upload(file) {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch("/convert", { method: "POST", body: form });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = file.name.replace(".m4a", ".mp3");
    a.click();
}
