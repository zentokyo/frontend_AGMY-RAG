import { Router } from 'express'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import crypto from 'crypto'
import { query } from '../db/index.js'

const router = Router()

const ACCESS_EXPIRES  = process.env.ACCESS_TOKEN_EXPIRES  || '15m'
const REFRESH_EXPIRES = process.env.REFRESH_TOKEN_EXPIRES || '7d'
const REFRESH_EXPIRES_MS = 7 * 24 * 60 * 60 * 1000

function signAccess(payload) {
  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: ACCESS_EXPIRES })
}

function signRefresh(payload) {
  return jwt.sign(payload, process.env.JWT_REFRESH_SECRET, { expiresIn: REFRESH_EXPIRES })
}

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex')
}

// POST /api/auth/login
router.post('/login', async (req, res, next) => {
  try {
    const { email, password } = req.body
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }

    const { rows } = await query('SELECT * FROM users WHERE email = $1', [email])
    const user = rows[0]
    if (!user) return res.status(401).json({ error: 'Invalid credentials' })

    const valid = await bcrypt.compare(password, user.password_hash)
    if (!valid) return res.status(401).json({ error: 'Invalid credentials' })

    const payload = { sub: user.id, email: user.email, role: user.role }
    const accessToken  = signAccess(payload)
    const refreshToken = signRefresh(payload)

    await query(
      `INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
      [user.id, hashToken(refreshToken)]
    )

    res.cookie('refreshToken', refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_EXPIRES_MS,
    })

    res.json({
      accessToken,
      user: { id: user.id, email: user.email, role: user.role },
    })
  } catch (err) {
    next(err)
  }
})

// POST /api/auth/refresh
router.post('/refresh', async (req, res, next) => {
  try {
    const token = req.cookies.refreshToken
    if (!token) return res.status(401).json({ error: 'No refresh token' })

    let payload
    try {
      payload = jwt.verify(token, process.env.JWT_REFRESH_SECRET)
    } catch {
      return res.status(401).json({ error: 'Invalid or expired refresh token' })
    }

    const hash = hashToken(token)
    const { rows } = await query(
      `SELECT * FROM refresh_tokens WHERE token_hash = $1 AND expires_at > NOW()`,
      [hash]
    )
    if (!rows.length) return res.status(401).json({ error: 'Refresh token revoked' })

    // Rotate: delete old, issue new
    await query('DELETE FROM refresh_tokens WHERE token_hash = $1', [hash])

    const newPayload     = { sub: payload.sub, email: payload.email, role: payload.role }
    const accessToken    = signAccess(newPayload)
    const newRefresh     = signRefresh(newPayload)

    await query(
      `INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
      [payload.sub, hashToken(newRefresh)]
    )

    res.cookie('refreshToken', newRefresh, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_EXPIRES_MS,
    })

    res.json({ accessToken })
  } catch (err) {
    next(err)
  }
})

// POST /api/auth/logout
router.post('/logout', async (req, res, next) => {
  try {
    const token = req.cookies.refreshToken
    if (token) {
      await query('DELETE FROM refresh_tokens WHERE token_hash = $1', [hashToken(token)])
    }
    res.clearCookie('refreshToken')
    res.json({ message: 'Logged out' })
  } catch (err) {
    next(err)
  }
})

// GET /api/auth/me — validate current access token
router.get('/me', (req, res) => {
  const authHeader = req.headers.authorization
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing token' })
  }
  try {
    const payload = jwt.verify(authHeader.slice(7), process.env.JWT_SECRET)
    res.json({ id: payload.sub, email: payload.email, role: payload.role })
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
})

export default router
