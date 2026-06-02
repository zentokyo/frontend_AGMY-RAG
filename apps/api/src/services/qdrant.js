/**
 * Qdrant vector DB client — поиск по векторной базе знаний.
 *
 * Конфигурация через переменные окружения:
 *   QDRANT_URL  — URL Qdrant REST API (по умолч. http://localhost:6333)
 *   QDRANT_COLLECTION — имя коллекции (по умолч. assistant_knowledge)
 */

import { QdrantClient } from '@qdrant/js-client-rest'

const QDRANT_URL = process.env.QDRANT_URL || 'http://localhost:6333'
const COLLECTION = process.env.QDRANT_COLLECTION || 'assistant_knowledge'
const VECTOR_SIZE = 1024  // GigaChat Embeddings (EmbeddingsGigaR)

let _client = null

function getClient() {
  if (!_client) {
    _client = new QdrantClient({ url: QDRANT_URL })
  }
  return _client
}

/**
 * Убедиться, что коллекция существует. Если нет — создать.
 */
export async function ensureCollection() {
  const client = getClient()
  const existing = await client.getCollections()
  const names = existing.collections.map((c) => c.name)
  if (names.includes(COLLECTION)) {
    console.log(`[qdrant] Collection "${COLLECTION}" already exists`)
    return
  }
  await client.createCollection(COLLECTION, {
    vectors: {
      size: VECTOR_SIZE,
      distance: 'Cosine',
    },
  })
  console.log(`[qdrant] Collection "${COLLECTION}" created (dim=${VECTOR_SIZE})`)
}

/**
 * Вставить/обновить точки (вектор + payload).
 * @param {Array<{id: string, vector: number[], payload: object}>} points
 */
export async function upsertPoints(points) {
  const client = getClient()
  await client.upsert(COLLECTION, {
    wait: true,
    points: points.map((p) => ({
      id: p.id,
      vector: p.vector,
      payload: p.payload,
    })),
  })
}

/**
 * Поиск релевантных чанков по вектору запроса.
 * @param {number[]} vector — эмбеддинг запроса (1024-мерный)
 * @param {object} [filter] — опциональный Qdrant-фильтр
 * @param {number} [limit=10]
 * @returns {Array<{id: string, score: number, payload: object}>}
 */
export async function searchPoints(vector, { filter, limit = 10 } = {}) {
  const client = getClient()
  const result = await client.search(COLLECTION, {
    vector,
    limit,
    filter,
    with_payload: true,
  })
  return result.map((r) => ({
    id: r.id,
    score: r.score,
    payload: r.payload || {},
  }))
}

/**
 * Удалить точки по ID.
 * @param {string[]} ids
 */
export async function deletePoints(ids) {
  const client = getClient()
  await client.delete(COLLECTION, {
    wait: true,
    points: ids,
  })
}

/**
 * Получить количество точек в коллекции.
 */
export async function countPoints() {
  const client = getClient()
  const info = await client.getCollection(COLLECTION)
  return info.points_count
}

export default {
  ensureCollection,
  upsertPoints,
  searchPoints,
  deletePoints,
  countPoints,
}
