/**
 * GigaChat Embeddings HTTP-клиент для Node.js.
 *
 * Использует GIGACHAT_AUTHORIZATION_KEY из окружения для аутентификации.
 * Токен кэшируется и обновляется автоматически.
 *
 * ВАЖНО: GigaChat использует самоподписанные сертификаты Минцифры РФ.
 * SSL-верификация отключена (аналогично Python-версии с GIGACHAT_VERIFY_SSL=False).
 */

import crypto from 'crypto'
import https from 'https'

const GIGACHAT_AUTH_HOST = 'ngw.devices.sberbank.ru'
const GIGACHAT_AUTH_PORT = 9443
const GIGACHAT_AUTH_PATH = '/api/v2/oauth'
const GIGACHAT_EMBEDDINGS_HOST = 'gigachat.devices.sberbank.ru'
const GIGACHAT_EMBEDDINGS_PORT = 443
const GIGACHAT_EMBEDDINGS_PATH = '/api/v1/embeddings'

let _cachedToken = null
let _tokenExpiresAt = 0

/**
 * HTTPS-запрос с самоподписанным сертификатом.
 * @param {object} opts — { hostname, port, path, method, headers }
 * @param {string} [body] — тело запроса
 * @returns {Promise<object>} — распарсенный JSON
 */
function httpsRequest(opts, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: opts.hostname,
        port: opts.port,
        path: opts.path,
        method: opts.method || 'GET',
        headers: opts.headers || {},
        rejectUnauthorized: false,  // Самоподписанный сертификат GigaChat
      },
      (res) => {
        let data = ''
        res.on('data', (chunk) => { data += chunk })
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(JSON.parse(data))
            } catch {
              resolve(data)
            }
          } else {
            reject(new Error(`GigaChat HTTP ${res.statusCode}: ${data.slice(0, 200)}`))
          }
        })
      }
    )
    req.on('error', reject)
    if (body) req.write(body)
    req.end()
  })
}

/**
 * Получить или обновить токен GigaChat.
 * @returns {Promise<string>}
 */
async function getToken() {
  const now = Date.now() / 1000
  if (_cachedToken && now < _tokenExpiresAt - 120) {
    return _cachedToken
  }

  const authKey = process.env.GIGACHAT_AUTHORIZATION_KEY
  if (!authKey) {
    throw new Error('GIGACHAT_AUTHORIZATION_KEY is not set')
  }

  const data = await httpsRequest({
    hostname: GIGACHAT_AUTH_HOST,
    port: GIGACHAT_AUTH_PORT,
    path: GIGACHAT_AUTH_PATH,
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',
      'RqUID': crypto.randomUUID(),
      'Authorization': `Basic ${authKey.trim()}`,
    },
  }, 'scope=GIGACHAT_API_PERS')

  _cachedToken = data.access_token
  _tokenExpiresAt = (data.expires_at || (Date.now() + 1800000)) / 1000

  console.log(`[gigachat] Token refreshed, expires in ${Math.round(_tokenExpiresAt - now)}s`)
  return _cachedToken
}

/**
 * Получить эмбеддинг для текстового запроса (1024-мерный вектор).
 * @param {string} text
 * @returns {Promise<number[]>}
 */
export async function embedQuery(text) {
  const token = await getToken()
  const data = await httpsRequest({
    hostname: GIGACHAT_EMBEDDINGS_HOST,
    port: GIGACHAT_EMBEDDINGS_PORT,
    path: GIGACHAT_EMBEDDINGS_PATH,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  }, JSON.stringify({ model: 'Embeddings', input: text }))

  return data.data[0].embedding
}

/**
 * Получить эмбеддинги для нескольких текстов.
 * @param {string[]} texts
 * @param {number} [batchSize=8]
 * @returns {Promise<number[][]>}
 */
export async function embedDocuments(texts, batchSize = 8) {
  const all = []
  for (let i = 0; i < texts.length; i += batchSize) {
    const batch = texts.slice(i, i + batchSize)
    const token = await getToken()
    const data = await httpsRequest({
      hostname: GIGACHAT_EMBEDDINGS_HOST,
      port: GIGACHAT_EMBEDDINGS_PORT,
      path: GIGACHAT_EMBEDDINGS_PATH,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    }, JSON.stringify({ model: 'Embeddings', input: batch }))

    all.push(...data.data.map((item) => item.embedding))
  }
  return all
}

export default { embedQuery, embedDocuments }
