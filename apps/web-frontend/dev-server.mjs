import { spawn } from 'node:child_process'
import http from 'node:http'
import net from 'node:net'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const host = process.env.FRONTEND_HOST || '127.0.0.1'
const publicPort = Number(process.env.FRONTEND_PORT || 5174)
const adminPort = Number(process.env.ADMIN_FRONTEND_PORT || 5173)
const chatPort = Number(process.env.CHAT_FRONTEND_PORT || 5175)
const apiBase = process.env.VITE_API_BASE || 'http://127.0.0.1:8001/api'
let server

const children = [
  startVite('admin', 'apps/admin-frontend', adminPort, '/admin/', '/_hmr/admin'),
  startVite('chat', 'apps/chat-frontend', chatPort, '/', '/_hmr/chat'),
]

await Promise.all([
  waitForPort(adminPort, 'admin frontend'),
  waitForPort(chatPort, 'chat frontend'),
])

server = http.createServer((req, res) => {
  if (req.url === '/admin') {
    res.writeHead(308, { location: '/admin/' })
    res.end()
    return
  }
  proxyHttp(req, res, routePort(req.url || '/'))
})

server.on('upgrade', (req, socket, head) => {
  proxyUpgrade(req, socket, head, routePort(req.url || '/'))
})

server.listen(publicPort, host, () => {
  console.log(`ASMU frontend dev server: http://${host}:${publicPort}`)
  console.log(`  chat:  http://${host}:${publicPort}/`)
  console.log(`  admin: http://${host}:${publicPort}/admin`)
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    for (const child of children) child.kill(signal)
    server.close(() => process.exit(0))
    setTimeout(() => process.exit(0), 2000).unref()
  })
}

function startVite(name, relativeDir, port, base, hmrPath) {
  const cwd = join(rootDir, relativeDir)
  const child = spawn(
    'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port), '--strictPort'],
    {
      cwd,
      env: {
        ...process.env,
        VITE_API_BASE: apiBase,
        VITE_BASE: base,
        VITE_DEV_PORT: String(port),
        VITE_HMR_CLIENT_PORT: String(publicPort),
        VITE_HMR_PATH: hmrPath,
        FORCE_COLOR: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  )

  child.stdout.on('data', (chunk) => process.stdout.write(prefixLog(name, chunk)))
  child.stderr.on('data', (chunk) => process.stderr.write(prefixLog(name, chunk)))
  child.on('exit', (code, signal) => {
    if (code === 0 || signal) return
    console.error(`[${name}] exited with code ${code}`)
    process.exitCode = code
    if (server) {
      server.close(() => process.exit(code))
    } else {
      process.exit(code)
    }
  })
  return child
}

function routePort(url) {
  if (url.startsWith('/admin') || url.startsWith('/_hmr/admin')) return adminPort
  return chatPort
}

function proxyHttp(req, res, port) {
  const headers = { ...req.headers, host: `127.0.0.1:${port}` }
  const proxyReq = http.request(
    {
      hostname: '127.0.0.1',
      port,
      method: req.method,
      path: req.url,
      headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers)
      proxyRes.pipe(res)
    },
  )

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' })
    res.end(`Frontend proxy error: ${error.message}`)
  })
  req.pipe(proxyReq)
}

function proxyUpgrade(req, socket, head, port) {
  const target = net.connect(port, '127.0.0.1', () => {
    target.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`)
    for (const [name, value] of Object.entries({ ...req.headers, host: `127.0.0.1:${port}` })) {
      if (Array.isArray(value)) {
        for (const item of value) target.write(`${name}: ${item}\r\n`)
      } else if (value !== undefined) {
        target.write(`${name}: ${value}\r\n`)
      }
    }
    target.write('\r\n')
    if (head.length > 0) target.write(head)
    socket.pipe(target).pipe(socket)
  })

  target.on('error', () => socket.destroy())
}

function waitForPort(port, label) {
  const deadline = Date.now() + 30_000
  return new Promise((resolveReady, rejectReady) => {
    const check = () => {
      const socket = net.createConnection({ host: '127.0.0.1', port }, () => {
        socket.end()
        resolveReady()
      })
      socket.on('error', () => {
        socket.destroy()
        if (Date.now() > deadline) {
          rejectReady(new Error(`${label} did not start on port ${port}`))
        } else {
          setTimeout(check, 250)
        }
      })
    }
    check()
  })
}

function prefixLog(name, chunk) {
  return String(chunk)
    .split('\n')
    .map((line, index, lines) => (line || index < lines.length - 1 ? `[${name}] ${line}` : line))
    .join('\n')
}
