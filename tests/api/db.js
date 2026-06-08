import pg from 'pg'

const { Pool } = pg

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT || process.env.POSTGRES_PUBLISHED_PORT || 5433),
  database: process.env.DB_NAME || process.env.POSTGRES_DB || 'assistant',
  user: process.env.DB_USER || process.env.POSTGRES_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD || 'example',
  max: 5,
  idleTimeoutMillis: 5_000,
  connectionTimeoutMillis: 2_000,
})

export const query = (text, params) => pool.query(text, params)
export const closeDb = () => pool.end()
