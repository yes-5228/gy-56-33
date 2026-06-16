const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = "";
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      if (data.detail) {
        message = data.detail;
      } else if (typeof data === "object") {
        const firstKey = Object.keys(data)[0];
        if (firstKey) {
          const val = data[firstKey];
          message = Array.isArray(val) ? val.join("；") : String(val);
        }
      }
    } catch {
      message = text;
    }
    throw new Error(message || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function get(path) {
  return request(path);
}

export function post(path, body) {
  return request(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function patch(path, body) {
  return request(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
