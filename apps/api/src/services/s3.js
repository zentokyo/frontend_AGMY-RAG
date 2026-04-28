/**
 * Storage service — abstracts between MinIO/S3 and local disk.
 *
 * Set STORAGE_TYPE=local in .env for development without MinIO.
 * Set STORAGE_TYPE=s3  (default) in production with MinIO running.
 */

import { S3Client, PutObjectCommand, DeleteObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3'
import { writeFile, unlink, access } from 'fs/promises'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { mkdirSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const LOCAL_UPLOADS_DIR = join(__dirname, '..', '..', 'uploads')
mkdirSync(LOCAL_UPLOADS_DIR, { recursive: true })

const STORAGE_TYPE = (process.env.STORAGE_TYPE || 's3').toLowerCase()

// ─── S3 client (lazy init) ──────────────────────────────────────────────────
let _s3 = null
function getS3() {
  if (!_s3) {
    _s3 = new S3Client({
      endpoint:    process.env.S3_ENDPOINT  || 'http://localhost:7000',
      region:      process.env.S3_REGION    || 'us-east-1',
      credentials: {
        accessKeyId:     process.env.S3_USER     || 'minioadmin',
        secretAccessKey: process.env.S3_PASSWORD || 'minioadmin',
      },
      forcePathStyle: true,
      requestHandler: { connectionTimeout: 3000, socketTimeout: 5000 },
    })
  }
  return _s3
}

const BUCKET = process.env.S3_BUCKET || 'assistant'

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Upload a file.
 * Throws a user-friendly Error on failure (never throws raw SDK errors).
 */
export async function uploadToS3(buffer, filename, mimetype = 'application/octet-stream') {
  if (STORAGE_TYPE === 'local') {
    await writeFile(join(LOCAL_UPLOADS_DIR, filename), buffer)
    console.log(`[storage:local] saved "${filename}"`)
    return
  }

  try {
    await getS3().send(new PutObjectCommand({
      Bucket:      BUCKET,
      Key:         filename,
      Body:        buffer,
      ContentType: mimetype,
      Metadata:    { original_filename: filename },
    }))
    console.log(`[storage:s3] uploaded "${filename}" → ${BUCKET}`)
  } catch (err) {
    const msg = err?.message || String(err)
    // Make connection errors actionable for the developer
    if (
      msg.includes('ECONNREFUSED') || msg.includes('ENOTFOUND') ||
      msg.includes('connect') || msg.includes('UnknownError') ||
      err?.name === 'UnknownError'
    ) {
      throw new Error(
        `Файловое хранилище (MinIO) недоступно. ` +
        `Запустите docker compose в AGMY_RAG или установите STORAGE_TYPE=local в apps/api/.env`
      )
    }
    throw new Error(`Ошибка загрузки файла в хранилище: ${msg}`)
  }
}

/**
 * Delete a file. Never throws — logs failures silently.
 */
export async function deleteFromS3(filename) {
  if (STORAGE_TYPE === 'local') {
    try {
      await unlink(join(LOCAL_UPLOADS_DIR, filename))
    } catch {
      // File may not exist — safe to ignore
    }
    return
  }

  try {
    await getS3().send(new DeleteObjectCommand({ Bucket: BUCKET, Key: filename }))
  } catch (err) {
    console.error(`[storage:s3] Failed to delete "${filename}":`, err?.message)
  }
}

/**
 * Check if a file exists.
 */
export async function existsInS3(filename) {
  if (STORAGE_TYPE === 'local') {
    try {
      await access(join(LOCAL_UPLOADS_DIR, filename))
      return true
    } catch {
      return false
    }
  }

  try {
    await getS3().send(new HeadObjectCommand({ Bucket: BUCKET, Key: filename }))
    return true
  } catch {
    return false
  }
}
