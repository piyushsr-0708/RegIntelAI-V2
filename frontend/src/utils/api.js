export const API_BASE_URL = 'http://localhost:8000';

export async function apiFetch(endpoint, options = {}) {
  const token = sessionStorage.getItem('regintel_jwt');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'API Request Failed');
  }

  // Handle empty responses (like 204 No Content)
  if (response.status === 204) {
    return null;
  }
  
  return response.json();
}
