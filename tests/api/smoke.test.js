import test from 'node:test'
import assert from 'node:assert/strict'

process.env.NODE_ENV = 'test'
process.env.CLIENT_ORIGIN = 'http://localhost:5173'

const { createApp } = await import('../../apps/api/src/app.js')

let server
let baseUrl

test.before(async () => {
  const app = createApp()
  server = app.listen(0)
  await new Promise((resolve) => server.once('listening', resolve))
  const { port } = server.address()
  baseUrl = `http://127.0.0.1:${port}`
})

test.after(async () => {
  if (server) {
    await new Promise((resolve, reject) => {
      server.close((err) => (err ? reject(err) : resolve()))
    })
  }
})

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
