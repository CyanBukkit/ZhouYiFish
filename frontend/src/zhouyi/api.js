const base = import.meta.env.VITE_API_BASE_URL ?? ''

export async function zhouyi(path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload.success === false) {
    const error = new Error(payload.error || `请求失败（${response.status}）`)
    error.payload = payload
    throw error
  }
  return payload.data
}
