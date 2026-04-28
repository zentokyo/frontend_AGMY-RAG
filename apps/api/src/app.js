import './env.js'
import express from 'express'
import cookieParser from 'cookie-parser'
import cors from 'cors'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { existsSync, mkdirSync } from 'fs'

import authRouter      from './routes/auth.js'
import documentsRouter from './routes/documents.js'
import questionsRouter from './routes/questions.js'
import appAuthRouter from './routes/app/auth.js'
import appExamsRouter from './routes/app/exams.js'
import appAnswersRouter from './routes/app/answers.js'
import appStatsRouter from './routes/app/stats.js'
import appThemesRouter from './routes/app/themes.js'

const __dirname = dirname(fileURLToPath(import.meta.url))

export function createApp() {
  const app = express()

  // Ensure uploads directory exists
  const uploadsDir = join(__dirname, '..', 'uploads')
  if (!existsSync(uploadsDir)) mkdirSync(uploadsDir, { recursive: true })

  const clientOrigin = process.env.CLIENT_ORIGIN || 'http://localhost:5173'
  const corsOrigin = clientOrigin.includes(',')
    ? clientOrigin.split(',').map((s) => s.trim())
    : clientOrigin

  app.use(cors({
    origin: corsOrigin,
    credentials: true,
  }))
  app.use(express.json())
  app.use(cookieParser())

  // API routes
  app.use('/api/auth', authRouter)
  app.use('/api/documents', documentsRouter)
  app.use('/api/questions', questionsRouter)
  app.use('/api/app/auth', appAuthRouter)
  app.use('/api/app', appExamsRouter)
  app.use('/api/app', appAnswersRouter)
  app.use('/api/app', appStatsRouter)
  app.use('/api/app', appThemesRouter)

  // Serve React build in production
  const publicDir = join(__dirname, '..', 'public')
  if (existsSync(publicDir)) {
    app.use(express.static(publicDir))
    app.get('*', (_req, res) => {
      res.sendFile(join(publicDir, 'index.html'))
    })
  }

  // Global error handler
  app.use((err, _req, res, _next) => {
    console.error(err)
    res.status(err.status || 500).json({ error: err.message || 'Internal server error' })
  })

  return app
}

export function startServer(port = process.env.PORT || 3001) {
  const app = createApp()
  return app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`)
  })
}

if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) {
  startServer()
}
