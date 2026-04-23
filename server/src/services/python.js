import { spawn } from 'child_process'
import { resolve } from 'path'

const PYTHON = process.env.PYTHON_PATH || 'python3'
const INGEST_SCRIPT  = resolve(process.env.INGEST_SCRIPT_PATH  || '../../ai_support/ingest.py')
const ADMIN_TOOLS    = resolve(process.env.ADMIN_TOOLS_PATH    || '../python/admin_tools.py')
const KB_PATH        = resolve(process.env.KB_PATH             || '../../ai_support/knowledge_base')
const CHROMA_DB_PATH = resolve(process.env.CHROMA_DB_PATH      || '../../ai_support/db_metadata_v5')

function runScript(scriptPath, args, cwd) {
  return new Promise((resolve, reject) => {
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
        resolve({ stdout, stderr })
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

/** Trigger incremental ingestion of the entire knowledge_base folder.
 *  ingest.py uses SHA-256 dedup so only new/changed files are embedded. */
export async function runIngest() {
  const scriptDir = INGEST_SCRIPT.substring(0, INGEST_SCRIPT.lastIndexOf('/'))
  return runScript(INGEST_SCRIPT, [], scriptDir)
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
