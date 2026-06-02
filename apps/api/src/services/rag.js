/**
 * RAG-сервис — проверка ответа студента по базе знаний.
 *
 * Flow:
 * 1. Векторизация вопроса через GigaChat Embeddings
 * 2. Поиск релевантных чанков в Qdrant
 * 3. Формирование промпта с контекстом
 * 4. Оценка ответа через DeepSeek V4 Flash
 *
 * Fallback: если RAG недоступен — точное сравнение (normalizedGiven === normalizedModel).
 */

import { embedQuery } from './embeddings.js'
import { searchPoints } from './qdrant.js'

const DEEPSEEK_API_URL = process.env.DEEPSEEK_API_URL || 'https://api.deepseek.com/v1/chat/completions'
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY
const DEEPSEEK_MODEL = process.env.DEEPSEEK_MODEL || 'deepseek-chat'

const MAX_CONTEXT_CHARS = parseInt(process.env.RAG_MAX_CONTEXT_CHARS || '3000', 10)
const SEARCH_LIMIT = parseInt(process.env.RAG_SEARCH_LIMIT || '10', 10)

/**
 * Проверить ответ студента с помощью RAG.
 *
 * @param {object} params
 * @param {string} params.question — текст вопроса
 * @param {string} params.answer — ответ студента
 * @param {string} [params.themeTitle] — название темы (фильтр поиска)
 * @returns {Promise<{is_correct: boolean, method: string, score?: number, error?: string}>}
 */
export async function evaluateAnswer({ question, answer, themeTitle }) {
  // ── 0. Базовая валидация ──────────────────────────────────────────────
  const txt = (answer || '').trim()
  if (!txt) {
    return { is_correct: false, method: 'empty' }
  }

  try {
    // ── 1. Векторизация вопроса ─────────────────────────────────────────
    let vector
    try {
      vector = await embedQuery(question)
    } catch (err) {
      console.error('[rag] GigaChat embeddings unavailable, using fallback:', err.message)
      return fallbackComparison(question, txt)
    }

    // ── 2. Поиск в Qdrant ────────────────────────────────────────────────
    const filter = themeTitle
      ? { must: [{ key: 'source_theme', match: { value: themeTitle } }] }
      : undefined

    const searchResult = await searchPoints(vector, { filter, limit: SEARCH_LIMIT })
    if (!searchResult.length) {
      console.warn('[rag] No relevant chunks found in Qdrant, using fallback')
      return fallbackComparison(question, txt)
    }

    // ── 3. Сбор контекста ────────────────────────────────────────────────
    let context = searchResult
      .map((r) => r.payload.text || '')
      .filter(Boolean)
      .join('\n\n')

    if (context.length > MAX_CONTEXT_CHARS) {
      context = context.slice(0, MAX_CONTEXT_CHARS)
    }

    // ── 4. Вызов DeepSeek ────────────────────────────────────────────────
    const prompt = `Ты — строгий экзаменатор по эпидемиологии и санитарным нормам.

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
${context}

ВОПРОС: ${question}
ОТВЕТ СТУДЕНТА: ${answer}

Оцени, верен ли ответ студента на основании контекста.
Ответ должен передавать ключевые факты правильно, дословное совпадение не требуется.
Если ответ содержит правильную суть — считай его верным.

Верни JSON одной строкой: {"verdict": "ВЕРНО", "explanation": "..."} или {"verdict": "НЕВЕРНО", "explanation": "..."}`

    const deepseekResult = await callDeepSeek(prompt)

    // ── 5. Парсинг результата ────────────────────────────────────────────
    const parsed = parseVerdict(deepseekResult)
    const isCorrect = parsed.verdict === 'ВЕРНО'

    return {
      is_correct: isCorrect,
      method: 'rag',
      score: isCorrect ? 1 : 0,
      ...(parsed.explanation ? { explanation: parsed.explanation } : {}),
    }
  } catch (err) {
    console.error('[rag] RAG pipeline error, falling back to exact comparison:', err.message)
    return fallbackComparison(question, txt)
  }
}

/**
 * Точное сравнение строк (fallback при недоступности RAG).
 */
function fallbackComparison(question, answer) {
  // Ищем модельны ответ в вопросе (если вопрос содержит ожидаемый ответ)
  // или просто сверяем — пока возвращаем undefined, вызывающая сторона
  // сама применит свою логику сравнения
  return { is_correct: null, method: 'fallback_required' }
}

/**
 * Вызов DeepSeek API.
 */
async function callDeepSeek(prompt) {
  if (!DEEPSEEK_API_KEY) {
    throw new Error('DEEPSEEK_API_KEY is not set')
  }

  const res = await fetch(DEEPSEEK_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${DEEPSEEK_API_KEY}`,
    },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 512,
      temperature: 0.0,
    }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`DeepSeek error ${res.status}: ${text}`)
  }

  const data = await res.json()
  return data.choices[0].message.content.trim()
}

/**
 * Парсинг JSON-вердикта из ответа DeepSeek (с запасом на нестрогий формат).
 */
function parseVerdict(raw) {
  try {
    // Ищем JSON в ответе
    const m = raw.match(/\{.*?\}/s)
    if (m) {
      return JSON.parse(m[0])
    }
  } catch {
    // fall through
  }

  // Фолбэк: ищем ключевые слова
  if (/верно|правильно|true/i.test(raw)) {
    return { verdict: 'ВЕРНО', explanation: 'Парсинг по ключевым словам' }
  }
  if (/неверно|неправильно|false/i.test(raw)) {
    return { verdict: 'НЕВЕРНО', explanation: 'Парсинг по ключевым словам' }
  }

  return { verdict: 'НЕВЕРНО', explanation: 'Формат ответа не распознан' }
}

export default { evaluateAnswer }
