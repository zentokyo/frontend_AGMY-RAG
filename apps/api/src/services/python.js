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

function runScript(scriptPath, args, cwd) {
  return new Promise((resolvePromise, reject) => {
    console.log(`[python] Spawning: ${PYTHON} ${scriptPath} ${args.join(' ')}`)
    const proc = spawn(PYTHON, [scriptPath, ...args], {
      cwd: cwd || process.cwd(),
      env: process.env,
    })

    let stdout = ''
    let stderr = ''
    proc.stdout.on('data', (d) => { stdout += d.toString() })
    proc.stderr.on('data', (d) => { stderr += d.toString() })

    proc.on('close', (code) => {
      if (code === 0) {
        console.log(`[python] Done: ${scriptPath}\n${stdout}`)
        resolvePromise({ stdout, stderr })
      } else {
        console.error(`[python] Error (code ${code}): ${stderr}`)
        reject(new Error(`Python script exited with code ${code}: ${stderr}`))
      }
    })

    proc.on('error', (err) => {
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
