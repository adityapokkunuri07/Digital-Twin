const BASE_URL = 'http://127.0.0.1:8000'

export const ApiClient = {
  get: async (path) => {
    const res = await fetch(`${BASE_URL}${path}`)
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json()
  },
  post: async (path, body = {}) => {
    const isFormData = body instanceof FormData;
    const options = {
      method: 'POST',
      body: isFormData ? body : JSON.stringify(body),
    };
    
    // Fetch automatically sets the correct Content-Type with boundary for FormData
    if (!isFormData) {
      options.headers = { 'Content-Type': 'application/json' };
    }
    
    const res = await fetch(`${BASE_URL}${path}`, options)
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
    return res.json()
  },
}
