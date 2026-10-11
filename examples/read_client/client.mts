/** Bounded read-only JSON requests. No authentication, mutation or model calls. */
export type ErrorCode =
  | 'invalid_options' | 'invalid_url' | 'aborted' | 'deadline' | 'network'
  | 'http' | 'media_type' | 'response_too_large' | 'invalid_json'
  | 'invalid_payload' | 'retry_later';

export class ClientError extends Error {
  constructor(readonly code: ErrorCode, readonly status?: number) {
    super(code);
    this.name = 'ClientError';
  }
}

export interface ReadOptions {
  maxAttempts?: number;
  deadlineMs?: number;
  retryDelayMs?: number;
  maxBytes?: number;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  /** Test-only allowance for literal loopback addresses; never enables other HTTP. */
  allowLoopbackHttp?: boolean;
}

function boundedInteger(value: number, low: number, high: number): number {
  if (!Number.isSafeInteger(value) || value < low || value > high) {
    throw new ClientError('invalid_options');
  }
  return value;
}

function discard(response: Response): void {
  // Cancellation is best effort and must not extend the request deadline.
  try { void response.body?.cancel().catch(() => {}); } catch { /* already locked */ }
}

/** Settle on abort even when an injected asynchronous dependency ignores its signal. */
function bound<T>(work: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const cleanup = () => signal.removeEventListener('abort', onAbort);
    const onAbort = () => { cleanup(); reject(signal.reason); };
    signal.addEventListener('abort', onAbort, { once: true });
    work.then(value => { cleanup(); resolve(value); }, error => { cleanup(); reject(error); });
    if (signal.aborted) onAbort();
  });
}

function pause(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const cleanup = () => { clearTimeout(timer); signal.removeEventListener('abort', onAbort); };
    const onAbort = () => { cleanup(); reject(signal.reason); };
    const timer = setTimeout(() => { cleanup(); resolve(); }, ms);
    signal.addEventListener('abort', onAbort, { once: true });
    if (signal.aborted) onAbort();
  });
}

async function parseBody(response: Response, maxBytes: number, signal: AbortSignal, deadline: number): Promise<unknown> {
  const mediaType = (response.headers.get('content-type') ?? '').split(';', 1)[0]!.trim().toLowerCase();
  if (mediaType !== 'application/json' && !/^application\/[a-z0-9!#$&^_.+-]+\+json$/.test(mediaType)) {
    discard(response);
    throw new ClientError('media_type', response.status);
  }
  const length = response.headers.get('content-length');
  if (length !== null && /^[0-9]+$/.test(length) && Number(length) > maxBytes) {
    discard(response);
    throw new ClientError('response_too_large', response.status);
  }
  const reader = response.body?.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  if (reader) {
    try {
      while (true) {
        // A synchronously productive stream can starve timer callbacks. Check elapsed
        // time while draining it, and do not retain empty chunks.
        if (performance.now() >= deadline) throw new ClientError('deadline');
        const chunk = await bound(reader.read(), signal);
        if (chunk.done) break;
        size += chunk.value.byteLength;
        if (size > maxBytes) throw new ClientError('response_too_large', response.status);
        if (chunk.value.byteLength > 0) chunks.push(chunk.value);
      }
    } catch (error) {
      void reader.cancel().catch(() => {});
      if (signal.aborted) throw signal.reason;
      if (error instanceof ClientError) throw error;
      throw new ClientError('network', response.status);
    } finally {
      reader.releaseLock();
    }
  }
  const bytes = new Uint8Array(size);
  let position = 0;
  for (const chunk of chunks) { bytes.set(chunk, position); position += chunk.byteLength; }
  try {
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) as unknown;
  } catch {
    throw new ClientError('invalid_json', response.status);
  }
}

export async function readJson<T>(endpoint: string | URL, decode: (input: unknown) => T | Promise<T>, options: ReadOptions = {}): Promise<T> {
  const allowed = new Set(['maxAttempts', 'deadlineMs', 'retryDelayMs', 'maxBytes', 'signal', 'fetchImpl', 'allowLoopbackHttp']);
  if (options === null || typeof options !== 'object' || Object.keys(options).some(key => !allowed.has(key)) || typeof decode !== 'function') {
    throw new ClientError('invalid_options');
  }
  const maxAttempts = boundedInteger(options.maxAttempts === undefined ? 3 : options.maxAttempts, 1, 5);
  const deadlineMs = boundedInteger(options.deadlineMs === undefined ? 1000 : options.deadlineMs, 1, 30_000);
  const retryDelayMs = boundedInteger(options.retryDelayMs === undefined ? 20 : options.retryDelayMs, 0, 1000);
  const maxBytes = boundedInteger(options.maxBytes === undefined ? 16_384 : options.maxBytes, 1, 65_536);
  if (options.allowLoopbackHttp !== undefined && typeof options.allowLoopbackHttp !== 'boolean') throw new ClientError('invalid_options');
  if (options.fetchImpl !== undefined && typeof options.fetchImpl !== 'function') throw new ClientError('invalid_options');
  const transport = options.fetchImpl ?? globalThis.fetch;
  if (typeof transport !== 'function' || (options.signal !== undefined && !(options.signal instanceof AbortSignal))) throw new ClientError('invalid_options');
  let url: URL;
  try {
    if (typeof endpoint !== 'string' && !(endpoint instanceof URL)) throw new Error();
    url = new URL(endpoint);
  } catch { throw new ClientError('invalid_url'); }
  const loopback = options.allowLoopbackHttp === true && url.protocol === 'http:'
    && (url.hostname === '127.0.0.1' || url.hostname === '[::1]');
  if ((url.protocol !== 'https:' && !loopback) || url.username || url.password || url.hash) throw new ClientError('invalid_url');

  const controller = new AbortController();
  const signal = controller.signal;
  const cancel = () => controller.abort(new ClientError('aborted'));
  const deadline = performance.now() + deadlineMs;
  const timer = setTimeout(() => controller.abort(new ClientError('deadline')), deadlineMs);
  options.signal?.addEventListener('abort', cancel, { once: true });
  if (options.signal?.aborted) cancel();
  const active = () => {
    if (signal.aborted) throw signal.reason;
    if (performance.now() >= deadline) throw new ClientError('deadline');
  };
  const transient = new Set([429, 502, 503, 504]);
  try {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      active();
      let response: Response;
      try {
        const pending = Promise.resolve().then(() => {
          active();
          return transport(url.href, {
            method: 'GET', credentials: 'omit', redirect: 'manual', cache: 'no-store',
            headers: { Accept: 'application/json' }, signal,
          });
        }).then(value => {
          if (signal.aborted) { discard(value); throw signal.reason; }
          return value;
        });
        response = await bound(pending, signal);
      } catch (error) {
        if (signal.aborted || error instanceof ClientError) throw signal.aborted ? signal.reason : error;
        if (!(error instanceof TypeError) || attempt === maxAttempts) throw new ClientError('network');
        await pause(Math.min(1000, retryDelayMs * 2 ** (attempt - 1)), signal);
        continue;
      }
      if (!response.ok) {
        discard(response);
        if (!transient.has(response.status) || attempt === maxAttempts) throw new ClientError('http', response.status);
        let delay = Math.min(1000, retryDelayMs * 2 ** (attempt - 1));
        const retryAfter = response.headers.get('retry-after');
        if (retryAfter !== null) {
          // Delta-seconds are supported. Refuse date/invalid forms rather than retry early.
          if (!/^[0-9]+$/.test(retryAfter)) throw new ClientError('retry_later', response.status);
          delay = Math.max(delay, Number(retryAfter) * 1000);
          if (!Number.isSafeInteger(delay) || delay >= deadline - performance.now()) throw new ClientError('retry_later', response.status);
        }
        await pause(delay, signal);
        continue;
      }
      const input = await parseBody(response, maxBytes, signal, deadline);
      active();
      let output: T;
      try {
        output = await bound(Promise.resolve().then(() => decode(input)), signal);
      } catch {
        if (signal.aborted) throw signal.reason;
        throw new ClientError('invalid_payload', response.status);
      }
      active();
      return output;
    }
    throw new ClientError('network'); // Exhaustiveness guard; every final attempt returns or throws.
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', cancel);
  }
}
