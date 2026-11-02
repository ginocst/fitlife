/* app.js: utilidades compartidas
La sesión la maneja Django con una cookie; aquí solo se envía el token CSRF. */

const $ = (selector) => document.querySelector(selector);

// Escapa texto antes de insertarlo como HTML (evita inyección de código / XSS)
const esc = (texto) =>
  String(texto ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );

const ZONA = document.querySelector('meta[name="zona-horaria"]').content;
const hora = (iso) =>
  new Date(iso).toLocaleTimeString("es-CL", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: ZONA,
  });
const dia = (iso) =>
  new Date(iso).toLocaleDateString("es-CL", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: ZONA,
  });

/* fetch a la API: envía la cookie de sesión (automático) y el token CSRF en los métodos que escriben */
async function api(url, { method = "GET", body = null } = {}) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = document.querySelector(
      'meta[name="csrf-token"]',
    ).content;
  }
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });
  if (res.status === 403 && method === "GET") {
    location.href = "/login/";
    return { ok: false, data: null };
  }
  const data = await res.json().catch(() => null);
  return { ok: res.ok, status: res.status, data };
}

/* Mensaje legible a partir de un error de la API */
function errorTexto(data) {
  if (!data) return "Ocurrió un error. Intenta nuevamente.";
  if (data.detail) return data.detail;
  return Object.values(data).flat().join(" ");
}
