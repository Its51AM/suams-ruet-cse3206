/* SUAMS Client Interaction Helpers */

function showToast(message, variant = "success") {
  const container = document.getElementById("suams-alert-region");
  if (!container) return;
  container.innerHTML = `
    <div class="alert alert-${variant} alert-dismissible fade show" role="alert">
      ${escapeHtml(message)}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

async function suamsFetch(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }
  return data;
}

async function markNotificationRead(notificationId) {
  try {
    await suamsFetch(`/api/notices/notifications/${notificationId}/read`, { method: "POST" });
    window.location.reload();
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function enrollInCourse(courseId) {
  try {
    await suamsFetch(`/api/courses/${courseId}/enroll`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    showToast("Enrolled in course successfully.", "success");
    setTimeout(() => window.location.reload(), 400);
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function deleteStudent(studentId) {
  try {
    await suamsFetch(`/api/students/${studentId}`, { method: "DELETE" });
    showToast("Student deleted.", "success");
    setTimeout(() => window.location.reload(), 400);
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function deleteCourse(courseId) {
  try {
    await suamsFetch(`/api/courses/${courseId}`, { method: "DELETE" });
    showToast("Course deleted.", "success");
    setTimeout(() => window.location.reload(), 400);
  } catch (err) {
    showToast(err.message, "danger");
  }
}
