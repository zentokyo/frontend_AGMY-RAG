import test from 'node:test'
import assert from 'node:assert/strict'

process.env.CLIENT_ORIGIN = 'http://127.0.0.1:5173'
process.env.PYTHON_API_URL ||= 'http://127.0.0.1:8001'
process.env.INTERNAL_API_TOKEN ||= 'change-me-internal-token'

const baseUrl = process.env.PYTHON_API_URL

test('GET /api/auth/me returns 401 without token', async () => {
  const res = await fetch(`${baseUrl}/api/auth/me`)
  assert.equal(res.status, 401)
})

test('POST /api/auth/login validates missing fields', async () => {
  const res = await fetch(`${baseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({}),
  })
  assert.equal(res.status, 400)
})

test('GET /api/questions requires bearer token', async () => {
  const res = await fetch(`${baseUrl}/api/questions`)
  assert.equal(res.status, 401)
})

test('GET / serves the admin SPA from FastAPI', async () => {
  const res = await fetch(`${baseUrl}/`)
  assert.equal(res.status, 200)
  assert.match(res.headers.get('content-type') || '', /text\/html/)
  assert.match(await res.text(), /<div id="root"><\/div>/)
})
