import { spawn } from 'child_process'
import { resolve, dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(__dirname, '..', '..', '..', '..')
const BACKEND_ROOT = resolve(process.env.BACKEND_ROOT || join(REPO_ROOT, 'backend'))

const PYTHON = process.env.PYTHON_PATH || 'python3'
const INGEST_SCRIPT = resolve(
  process.env.INGEST_SCRIPT_PATH || join(BACKEND_ROOT, 'src/core/rag/ingest.py')
)
const ADMIN_TOOLS = resolve(
  process.env.ADMIN_TOOLS_PATH || join(REPO_ROOT, 'python', 'admin_tools.py')
)
const KB_PATH = resolve(process.env.KB_PATH || join(BACKEND_ROOT, 'knowledge_base'))
const CHROMA_DB_PATH = resolve(
  process.env.CHROMA_DB_PATH || join(BACKEND_ROOT, 'src/core/rag/db_metadata_v5')
)

// Таймаут для Python-процессов (по умолчанию 10 минут — инжест может быть долгим)
const PYTHON_TIMEOUT_MS = parseInt(process.env.PYTHON_TIMEOUT_MS || '600000', 10)

// Ограничение одновременных Python-процессов
const MAX_CONCURRENT = parseInt(process.env.MAX_PYTHON_CONCURRENT || '2', 10)
let _runningCount = 0

function runScript(scriptPath, args, cwd) {
  return new Promise((resolvePromise, reject) => {
    if (_runningCount >= MAX_CONCURRENT) {
      return reject(new Error(
        `Too many concurrent Python processes (${_runningCount}/${MAX_CONCURRENT}). Try again later.`
      ))
    }

    _runningCount++
    console.log(`[python] Spawning: ${PYTHON} ${scriptPath} ${args.join(' ')} (running: ${_runningCount}/${MAX_CONCURRENT})`)

    const proc = spawn(PYTHON, [scriptPath, ...args], {
      cwd: cwd || process.cwd(),
      env: process.env,
    })

    let stdout = ''
    let stderr = ''
    let finished = false

    // Таймаут: убить процесс, если он работает слишком долго
    const timer = setTimeout(() => {
      if (!finished) {
        finished = true
        _runningCount--
        proc.kill('SIGTERM')
        console.error(`[python] Timeout after ${PYTHON_TIMEOUT_MS}ms: ${scriptPath}`)
        reject(new Error(`Python script timed out after ${PYTHON_TIMEOUT_MS}ms: ${scriptPath}`))
      }
    }, PYTHON_TIMEOUT_MS)

    proc.stdout.on('data', (d) => { stdout += d.toString() })
    proc.stderr.on('data', (d) => { stderr += d.toString() })

    proc.on('close', (code) => {
      if (finished) return  // уже обработали через таймаут
      finished = true
      _runningCount--
      clearTimeout(timer)

      if (code === 0) {
        console.log(`[python] Done: ${scriptPath}\n${stdout}`)
        resolvePromise({ stdout, stderr })
      } else {
        console.error(`[python] Error (code ${code}): ${stderr}`)
        reject(new Error(`Python script exited with code ${code}: ${stderr}`))
      }
    })

    proc.on('error', (err) => {
      if (finished) return
      finished = true
      _runningCount--
      clearTimeout(timer)
      reject(new Error(`Failed to spawn python process: ${err.message}`))
    })
  })
}

/** Run RAG ingest; cwd must be backend root so paths in ingest.py resolve. */
export async function runIngest() {
  return runScript(INGEST_SCRIPT, [], BACKEND_ROOT)
}

/** Delete all ChromaDB chunks that belong to the given file. */
export async function deleteFromChroma(storedFilename) {
  const filePath = `${KB_PATH}/${storedFilename}`
  return runScript(ADMIN_TOOLS, [
    '--action', 'delete',
    '--file', filePath,
    '--db-path', CHROMA_DB_PATH,
  ])
}

/** Run ingest into Qdrant (replaces ChromaDB). */
const INGEST_QDRANT_SCRIPT = resolve(
  process.env.INGEST_QDRANT_SCRIPT_PATH || join(BACKEND_ROOT, 'src/core/rag/ingest_qdrant.py')
)

export async function runIngestQdrant(incremental = false) {
  const args = incremental ? ['--incremental'] : []
  return runScript(INGEST_QDRANT_SCRIPT, args, BACKEND_ROOT)
}
