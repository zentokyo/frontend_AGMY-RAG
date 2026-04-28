import dotenv from 'dotenv'
import { existsSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const apiDir = resolve(__dirname, '..')
const repoRoot = resolve(__dirname, '..', '..', '..')

if (existsSync(resolve(repoRoot, '.env'))) {
  dotenv.config({ path: resolve(repoRoot, '.env') })
}
if (existsSync(resolve(apiDir, '.env'))) {
  dotenv.config({ path: resolve(apiDir, '.env'), override: true })
}
