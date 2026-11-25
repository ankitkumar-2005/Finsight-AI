export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export async function apiRequest(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    })
  } catch {
    throw new Error('FinSight could not reach the API. Check that the Flask server is running and try again.')
  }
  let payload
  try { payload = await response.json() } catch { payload = {} }
  if (!response.ok) {
    const error = new Error(payload.error || 'The request could not be completed.')
    error.status = response.status
    error.fieldErrors = payload.field_errors || {}
    throw error
  }
  return payload
}
