const tokenInput = document.querySelector("#token");
const statusBox = document.querySelector("#status");
const title = document.querySelector("#view-title");

function token() {
  return tokenInput.value.trim();
}

function setStatus(message) {
  statusBox.textContent = typeof message === "string" ? message : JSON.stringify(message, null, 2);
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw data;
  return data;
}

document.querySelectorAll("nav button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.view}`).classList.add("active");
    title.textContent = button.textContent;
  });
});

document.querySelectorAll("form[data-endpoint]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = form.querySelector("input[type=file]").files[0];
    if (!file) return setStatus("Choose a file first.");
    const data = new FormData();
    data.append("file", file);
    try {
      setStatus(await api(form.dataset.endpoint, { method: "POST", body: data }));
    } catch (error) {
      setStatus(error);
    }
  });
});

document.querySelector("#load-report").addEventListener("click", async () => {
  try {
    const rows = await api("/admin/reports/attendance");
    document.querySelector("#report-body").innerHTML = rows
      .map((row) => `<tr><td>${row.subject_code}</td><td>${row.subject_name}</td><td>${row.present_records}</td></tr>`)
      .join("");
    setStatus(`Loaded ${rows.length} report rows.`);
  } catch (error) {
    setStatus(error);
  }
});

document.querySelector("#load-defaulters").addEventListener("click", async () => {
  try {
    const rows = await api("/admin/reports/defaulters");
    document.querySelector("#defaulter-body").innerHTML = rows
      .map((row) => `<tr><td>${row.usn}</td><td>${row.student_name}</td><td>${row.subject_code}</td><td>${row.percentage}</td></tr>`)
      .join("");
    setStatus(`Loaded ${rows.length} defaulter rows.`);
  } catch (error) {
    setStatus(error);
  }
});

