/**
 * Shared helpers for calling the ENY backend.
 *
 * Background: a backend 500 used to reach the browser without CORS headers, so the
 * only thing the UI could show was the browser's "NetworkError when attempting to
 * fetch resource". These helpers turn transport failures and error payloads into
 * messages a user can act on, and bound long-running requests so the UI never hangs.
 */

export const API_TIMEOUTS = {
  /** Regular JSON reads and writes. */
  standard: 20_000,
  /** Knowledge ingest embeds every chunk, so it is legitimately slow. */
  knowledgeIngest: 180_000,
} as const

const BROWSER_NETWORK_ERROR_PATTERNS = [
  'failed to fetch',
  'networkerror',
  'network error',
  'load failed',
  'connection refused',
  'econnrefused',
]

const UNREACHABLE_API_MESSAGE =
  'Could not reach the ENY API. Check your connection, then retry. If it keeps failing, the API may be down.'

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function isNetworkError(error: unknown): boolean {
  if (!(error instanceof Error)) return false
  const message = error.message.toLowerCase()
  return BROWSER_NETWORK_ERROR_PATTERNS.some((pattern) => message.includes(pattern))
}

/** Turn a thrown transport error into an actionable message. */
export function describeRequestFailure(error: unknown, fallback: string, timeoutMs?: number): string {
  if (isAbortError(error)) {
    const seconds = timeoutMs ? Math.round(timeoutMs / 1000) : undefined
    return seconds
      ? `The request timed out after ${seconds}s. The server is still processing; retry in a moment.`
      : 'The request timed out. The server is still processing; retry in a moment.'
  }
  if (isNetworkError(error)) return UNREACHABLE_API_MESSAGE
  if (error instanceof Error && error.message) return error.message
  return fallback
}

/** fetch with an AbortController deadline; transport failures are already described. */
export async function fetchWithTimeout(
  input: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(input, { ...init, signal: controller.signal })
  } catch (error) {
    throw new Error(describeRequestFailure(error, 'The request failed.', timeoutMs))
  } finally {
    clearTimeout(timer)
  }
}

async function parseErrorBody(response: Response): Promise<unknown> {
  try {
    const raw = await response.text()
    if (!raw) return null
    try {
      return JSON.parse(raw)
    } catch {
      return raw
    }
  } catch {
    return null
  }
}

function extractDetailMessage(body: unknown): string | null {
  if (typeof body === 'string') return body.trim() || null
  if (!body || typeof body !== 'object') return null
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail.trim() || null
  if (detail && typeof detail === 'object') {
    const nested = (detail as { message?: unknown }).message
    if (typeof nested === 'string') return nested.trim() || null
  }
  const message = (body as { message?: unknown }).message
  if (typeof message === 'string') return message.trim() || null
  return null
}

/**
 * Read the failure reason from a non-OK response. Falls back to a status-aware
 * message when the body is empty, HTML, or not JSON.
 */
export async function describeHttpError(response: Response, fallback: string): Promise<string> {
  const detail = extractDetailMessage(await parseErrorBody(response))
  if (detail) return detail

  if (response.status === 429) {
    const retryAfter = response.headers.get('retry-after')
    return retryAfter
      ? `The service is rate limiting requests. Retry in ${retryAfter}s.`
      : 'The service is rate limiting requests. Wait a moment and retry.'
  }
  if (response.status === 503) return `${fallback} The service is temporarily unavailable.`
  if (response.status === 401 || response.status === 403) {
    return 'You do not have permission to perform this action. Sign in again if your session expired.'
  }
  return `${fallback} (HTTP ${response.status})`
}
