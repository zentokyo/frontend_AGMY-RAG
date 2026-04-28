import jwt from 'jsonwebtoken'

export function requireAppAuth(req, res, next) {
  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing authorization token' })
  }

  const token = authHeader.slice(7)
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET)
    if (payload.type !== 'app') {
      return res.status(403).json({ error: 'Invalid token type' })
    }
    req.appUser = { id: payload.sub, email: payload.email, username: payload.username ?? null }
    next()
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' })
  }
}
