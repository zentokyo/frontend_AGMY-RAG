import { Router } from 'express'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'
import crypto from 'crypto'
import { query } from '../../db/index.js'
import { requireAppAuth } from '../../middleware/appAuth.js'

const router = Router()

const ACCESS_EXPIRES = process.env.ACCESS_TOKEN_EXPIRES || '15m'
const REFRESH_EXPIRES = process.env.REFRESH_TOKEN_EXPIRES || '7d'
const REFRESH_EXPIRES_MS = 7 * 24 * 60 * 60 * 1000
const COOKIE_NAME = 'appRefreshToken'

function signAccess(payload) {
  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: ACCESS_EXPIRES })
}

function signRefresh(payload) {
  return jwt.sign(payload, process.env.JWT_REFRESH_SECRET, { expiresIn: REFRESH_EXPIRES })
}

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex')
}

router.post('/register', async (req, res, next) => {
  try {
    const { email, password, username } = req.body
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }
    if (String(password).length < 6) {
      return res.status(400).json({ error: 'Password must be at least 6 characters' })
    }

    const existing = await query('SELECT id FROM app_users WHERE email = $1', [email.toLowerCase().trim()])
    if (existing.rows.length) {
      return res.status(409).json({ error: 'User already exists' })
    }

    const passwordHash = await bcrypt.hash(password, 12)
    const { rows } = await query(
      `INSERT INTO app_users (email, password_hash, username)
       VALUES ($1, $2, $3)
       RETURNING id, email, username, created_at`,
      [email.toLowerCase().trim(), passwordHash, username?.trim() || null]
    )
    const user = rows[0]

    const payload = { sub: user.id, email: user.email, username: user.username, type: 'app' }
    const accessToken = signAccess(payload)
    const refreshToken = signRefresh(payload)

    await query(
      `INSERT INTO app_refresh_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
      [user.id, hashToken(refreshToken)]
    )

    res.cookie(COOKIE_NAME, refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_EXPIRES_MS,
    })

    res.status(201).json({
      accessToken,
      user: { id: user.id, email: user.email, username: user.username },
    })
  } catch (err) {
    next(err)
  }
})

router.post('/login', async (req, res, next) => {
  try {
    const { email, password } = req.body
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }

    const { rows } = await query('SELECT * FROM app_users WHERE email = $1', [email.toLowerCase().trim()])
    const user = rows[0]
    if (!user) return res.status(401).json({ error: 'Invalid credentials' })

    const valid = await bcrypt.compare(password, user.password_hash)
    if (!valid) return res.status(401).json({ error: 'Invalid credentials' })

    const payload = { sub: user.id, email: user.email, username: user.username, type: 'app' }
    const accessToken = signAccess(payload)
    const refreshToken = signRefresh(payload)

    await query(
      `INSERT INTO app_refresh_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
      [user.id, hashToken(refreshToken)]
    )

    res.cookie(COOKIE_NAME, refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: REFRESH_EXPIRES_MS,
    })

    res.json({
      accessToken,
      user: { id: user.id, email: user.email, username: user.username },
    })
  } catch (err) {
    next(err)
  }
})

router.post('/refresh', async (req, res, next) => {
  try {
    const token = req.cookies[COOKIE_NAME]
    if (!token) return res.status(401).json({ error: 'No refresh token' })

    let payload
    try {
      payload = jwt.verify(token, process.env.JWT_REFRESH_SECRET)
    } catch {
      return res.status(401).json({ error: 'Invalid or expired refresh token' })
    }
    if (payload.type !== 'app') return res.status(403).json({ error: 'Invalid token type' })

    const hash = hashToken(token)
    const { rows } = await query(
      `SELECT * FROM app_refresh_tokens WHERE token_hash = $1 AND expires_at > NOW()`,
      [hash]
    )
    if (!rows.length) return res.status(401).json({ error: 'Refresh token revoked' })

    await query('DELETE FROM app_refresh_tokens WHERE token_hash = $1', [hash])

    const nextPayload = {
      sub: payload.sub,
      email: payload.email,
      username: payload.username ?? null,
      type: 'app',
    }
    const accessToken = signAccess(nextPayload)
    const nextRefresh = signRefresh(nextPayload)
    await query(
      `INSERT INTO app_refresh_tokens (user_id, token_hash, expires_at)
       VALUES ($1, $2, NOW() + INTERVAL '7 days')`,
      [payload.sub, hashToken(nextRefresh)]
    )

    res.cookie(COOKIE_NAME, nextRefresh, {
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

router.post('/logout', async (req, res, next) => {
  try {
    const token = req.cookies[COOKIE_NAME]
    if (token) {
      await query('DELETE FROM app_refresh_tokens WHERE token_hash = $1', [hashToken(token)])
    }
    res.clearCookie(COOKIE_NAME)
    res.json({ message: 'Logged out' })
  } catch (err) {
    next(err)
  }
})

router.get('/me', requireAppAuth, async (req, res) => {
  res.json({ user: req.appUser })
})

export default router
