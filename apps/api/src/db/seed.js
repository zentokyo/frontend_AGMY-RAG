import '../env.js'
import bcrypt from 'bcryptjs'
import pool from './index.js'

async function seed() {
  const email    = process.env.SEED_ADMIN_EMAIL    || 'admin@example.com'
  const password = process.env.SEED_ADMIN_PASSWORD || 'Admin123!'

  const hash = await bcrypt.hash(password, 12)

  const { rows } = await pool.query(
    `INSERT INTO admin_users (email, password_hash, role)
     VALUES ($1, $2, 'admin')
     ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
     RETURNING id, email`,
    [email, hash]
  )

  console.log(`Admin user seeded: ${rows[0].email} (id=${rows[0].id})`)
  await pool.end()
}

seed().catch((err) => {
  console.error('Seed failed:', err)
  process.exit(1)
})
