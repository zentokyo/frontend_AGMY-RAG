import { S3Client, PutObjectCommand, DeleteObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3'

const s3 = new S3Client({
  endpoint:         process.env.S3_ENDPOINT  || 'http://localhost:7000',
  region:           process.env.S3_REGION    || 'us-east-1',
  credentials: {
    accessKeyId:     process.env.S3_USER     || 'minioadmin',
    secretAccessKey: process.env.S3_PASSWORD || 'minioadmin',
  },
  forcePathStyle: true, // required for MinIO
})

const BUCKET = process.env.S3_BUCKET || 'assistant'

/**
 * Upload a file buffer to MinIO.
 * @param {Buffer} buffer
 * @param {string} filename  — stored as the S3 object key (same as AGMY_RAG convention)
 * @param {string} mimetype
 */
export async function uploadToS3(buffer, filename, mimetype = 'application/octet-stream') {
  await s3.send(new PutObjectCommand({
    Bucket:      BUCKET,
    Key:         filename,
    Body:        buffer,
    ContentType: mimetype,
    Metadata: {
      original_filename: filename,
    },
  }))
}

/**
 * Delete a file from MinIO by filename (= S3 key).
 */
export async function deleteFromS3(filename) {
  try {
    await s3.send(new DeleteObjectCommand({ Bucket: BUCKET, Key: filename }))
  } catch (err) {
    // Log but don't throw — DB record is already removed; S3 orphan is acceptable
    console.error(`[s3] Failed to delete "${filename}":`, err.message)
  }
}

/**
 * Check if a file exists in MinIO.
 */
export async function existsInS3(filename) {
  try {
    await s3.send(new HeadObjectCommand({ Bucket: BUCKET, Key: filename }))
    return true
  } catch {
    return false
  }
}
