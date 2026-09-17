const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function checkHealth(signal: AbortSignal): Promise<void> {
  const response = await fetch(`${baseUrl}/health`, { signal })
  if (response.status !== 200) throw new Error('Health unavailable')
  const body: unknown = await response.json()
  if (
    typeof body !== 'object' || body === null ||
    Object.keys(body).length !== 2 ||
    !('status' in body) || body.status !== 'ok' ||
    !('database' in body) || body.database !== 'ok'
  ) throw new Error('Unexpected health response')
}
