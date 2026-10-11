import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

if (!process.env.SDK_MODULE) throw new Error('Run python tools/verify.py --component sdk from the repository root.');
const { readJson } = await import(pathToFileURL(process.env.SDK_MODULE));
const ENDPOINT = 'https://unit.invalid/data';
const decode = (value) => {
  if (value === null || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).length !== 1 || !Number.isSafeInteger(value.count)) {
    throw new Error('expected a single integer count');
  }
  return { count: value.count };
};
const jsonResponse = (body = '{"count":7}', status = 200, headers = {}) =>
  new Response(body, { status, headers: { 'content-type': 'application/json', ...headers } });
const code = (expected) => (error) => error?.code === expected;
const options = (fetchImpl, extra = {}) => ({ fetchImpl, retryDelayMs: 0, deadlineMs: 500, ...extra });

// Most transports below are deterministic fakes; the final test uses an actual loopback server.
test('decodes JSON and sends GET without cookies or automatic redirects', async () => {
  let seen;
  const value = await readJson(ENDPOINT, decode, options(async (url, init) => {
    seen = { url, init }; return jsonResponse();
  }));
  assert.deepEqual(value, { count: 7 });
  assert.equal(seen.init.method, 'GET');
  assert.equal(seen.init.credentials, 'omit');
  assert.equal(seen.init.redirect, 'manual');
  assert.equal(seen.init.headers.Accept, 'application/json');
});

test('retries transient GET and discards the failed response body', async () => {
  let attempts = 0; let discarded = false;
  const response = new Response(new ReadableStream({ cancel() { discarded = true; } }), { status: 503 });
  const result = await readJson(ENDPOINT, decode, options(async () => ++attempts === 1 ? response : jsonResponse()));
  assert.deepEqual(result, { count: 7 });
  assert.equal(attempts, 2); assert.equal(discarded, true);
});

test('stops at the attempt budget', async () => {
  let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse('{}', 503); }, { maxAttempts: 2 })), code('http'));
  assert.equal(attempts, 2);
});

test('retries a simulated network failure for GET only', async () => {
  let attempts = 0;
  const result = await readJson(ENDPOINT, decode, options(async () => {
    if (++attempts === 1) throw new TypeError('synthetic network failure');
    return jsonResponse();
  }));
  assert.equal(result.count, 7); assert.equal(attempts, 2);
});

test('authorization and client errors never retry or echo server text', async () => {
  for (const status of [400, 401, 403, 404]) {
    let attempts = 0;
    await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse('synthetic diagnostic', status); })),
      (error) => error.code === 'http' && error.status === status && !error.message.includes('synthetic diagnostic'));
    assert.equal(attempts, 1);
  }
});

test('invalid JSON does not retry', async () => {
  let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse('{broken'); })), code('invalid_json'));
  assert.equal(attempts, 1);
});

test('runtime schema errors do not retry', async () => {
  let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse('{"count":1e309}'); })), code('invalid_payload'));
  assert.equal(attempts, 1);
});

test('rejects incorrect media type', async () => {
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response('{"count":7}', { headers: { 'content-type': 'text/html' } }))), code('media_type'));
});

test('accepts structured JSON media types', async () => {
  const value = await readJson(ENDPOINT, decode, options(async () => jsonResponse('{"count":7}', 200, { 'content-type': 'application/example+json; charset=utf-8' })));
  assert.equal(value.count, 7);
});

test('caps streamed response bytes without relying on content-length', async () => {
  let cancelled = false;
  const body = new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array(6)); },
    cancel() { cancelled = true; }
  });
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response(body, { headers: { 'content-type': 'application/json' } }), { maxBytes: 5 })), code('response_too_large'));
  assert.equal(cancelled, true);
});

test('rejects excessive declared content-length and cancels body', async () => {
  let cancelled = false;
  const body = new ReadableStream({ cancel() { cancelled = true; } });
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response(body, { headers: { 'content-type': 'application/json', 'content-length': '100' } }), { maxBytes: 20 })), code('response_too_large'));
  assert.equal(cancelled, true);
});

test('invalid UTF-8 is not silently repaired', async () => {
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response(new Uint8Array([255]), { headers: { 'content-type': 'application/json' } }))), code('invalid_json'));
});

test('unsafe URL forms are rejected before invoking transport', async () => {
  const embedded = new URL(ENDPOINT); embedded.username = 'synthetic';
  for (const url of ['http://unit.invalid/data', 'file:///synthetic.json', `${ENDPOINT}#fragment`, embedded.href]) {
    let attempts = 0;
    await assert.rejects(readJson(url, decode, options(async () => { attempts++; return jsonResponse(); })), code('invalid_url'));
    assert.equal(attempts, 0);
  }
});

test('loopback exception does not allow non-loopback HTTP', async () => {
  await assert.rejects(readJson('http://unit.invalid/data', decode, options(async () => jsonResponse(), { allowLoopbackHttp: true })), code('invalid_url'));
});

test('pre-aborted request does not invoke transport', async () => {
  const controller = new AbortController(); controller.abort(); let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse(); }, { signal: controller.signal })), code('aborted'));
  assert.equal(attempts, 0);
});

test('caller cancellation settles even when injected transport ignores signal', { timeout: 1000 }, async () => {
  const controller = new AbortController(); let attempts = 0;
  const result = readJson(ENDPOINT, decode, options(() => { attempts++; return new Promise(() => {}); }, { signal: controller.signal }));
  const timer = setTimeout(() => controller.abort(), 5);
  try { await assert.rejects(result, code('aborted')); } finally { clearTimeout(timer); }
  assert.equal(attempts, 1);
});

test('one overall deadline bounds a non-cooperative transport', { timeout: 1000 }, async () => {
  await assert.rejects(readJson(ENDPOINT, decode, options(() => new Promise(() => {}), { deadlineMs: 10 })), code('deadline'));
});

test('cancellation during backoff prevents the next request', { timeout: 1000 }, async () => {
  const controller = new AbortController(); let attempts = 0;
  const result = readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse('{}', 503); },
    { retryDelayMs: 1000, signal: controller.signal }));
  const timer = setTimeout(() => controller.abort(), 5);
  try { await assert.rejects(result, code('aborted')); } finally { clearTimeout(timer); }
  assert.equal(attempts, 1);
});

test('deadline also bounds a stalled response body and cancels its reader', { timeout: 1000 }, async () => {
  let cancelled = false;
  const body = new ReadableStream({ cancel() { cancelled = true; } });
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response(body, { headers: { 'content-type': 'application/json' } }), { deadlineMs: 10 })), code('deadline'));
  assert.equal(cancelled, true);
});

test('long or unsupported Retry-After stops instead of retrying early', async () => {
  for (const header of ['3600', 'unsupported-date-form']) {
    let attempts = 0;
    await assert.rejects(readJson(ENDPOINT, decode, options(async () => {
      attempts++; return jsonResponse('{}', 429, { 'retry-after': header });
    })), code('retry_later'));
    assert.equal(attempts, 1);
  }
});

test('zero-second Retry-After allows a bounded retry', async () => {
  let attempts = 0;
  const result = await readJson(ENDPOINT, decode, options(async () => ++attempts === 1
    ? jsonResponse('{}', 429, { 'retry-after': '0' }) : jsonResponse()));
  assert.equal(result.count, 7); assert.equal(attempts, 2);
});

test('option bounds fail before invoking transport', async () => {
  for (const extra of [{ maxAttempts: 0 }, { maxAttempts: 6 }, { maxAttempts: true },
    { deadlineMs: Infinity }, { deadlineMs: 0 }, { retryDelayMs: NaN }, { maxBytes: 0 },
    { maxBytes: 65_537 }, { allowLoopbackHttp: 'yes' }]) {
    let attempts = 0;
    await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse(); }, extra)), code('invalid_options'));
    assert.equal(attempts, 0);
  }
});

test('redirect response is terminal and its body is discarded', async () => {
  let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return new Response('', { status: 302, headers: { location: 'https://unit.invalid/other' } }); })), code('http'));
  assert.equal(attempts, 1);
});

test('unexpected transport exceptions are terminal', async () => {
  let attempts = 0;
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; throw new Error('synthetic configuration failure'); })), code('network'));
  assert.equal(attempts, 1);
});

test('real loopback HTTP retries 503, decodes JSON, and never follows redirect', { timeout: 3000 }, async () => {
  let reads = 0; let redirects = 0; let targets = 0;
  const server = createServer((request, response) => {
    if (request.url === '/redirect') { redirects++; response.writeHead(302, { Location: '/target' }); response.end(); return; }
    if (request.url === '/target') targets++;
    if (request.url === '/data') reads++;
    response.writeHead(reads === 1 ? 503 : 200, { 'content-type': 'application/json', 'retry-after': '0' });
    response.end('{"count":7}');
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    const origin = `http://127.0.0.1:${server.address().port}`;
    const opt = { allowLoopbackHttp: true, retryDelayMs: 0, deadlineMs: 1500 };
    assert.deepEqual(await readJson(`${origin}/data`, decode, opt), { count: 7 });
    assert.equal(reads, 2);
    await assert.rejects(readJson(`${origin}/redirect`, decode, opt), (error) => error.code === 'http' && error.status === 302);
    assert.equal(redirects, 1); assert.equal(targets, 0);
  } finally {
    const closed = once(server, 'close'); server.close(); server.closeAllConnections(); await closed;
  }
});

test('empty chunks cannot starve the overall body-read deadline', { timeout: 1000 }, async () => {
  let pulls = 0;
  const body = new ReadableStream({
    pull(controller) {
      pulls++;
      if (pulls % 100 === 0) {
        const end = performance.now() + 1;
        while (performance.now() < end) { /* bounded synthetic producer work */ }
      }
      if (pulls <= 5000) controller.enqueue(new Uint8Array());
      else controller.close();
    }
  });
  await assert.rejects(readJson(ENDPOINT, decode, options(async () => new Response(body,
    { headers: { 'content-type': 'application/json' } }), { deadlineMs: 10 })), code('deadline'));
  assert.ok(pulls < 5000, 'must stop draining the producer after the deadline');
});

test('asynchronous validation is included in the same deadline', { timeout: 1000 }, async () => {
  const slowDecode = async () => {
    await new Promise(resolve => setTimeout(resolve, 40));
    return { count: 7 };
  };
  await assert.rejects(readJson(ENDPOINT, slowDecode, options(async () => jsonResponse(), { deadlineMs: 10 })), code('deadline'));
});

test('null numeric options are invalid rather than silent defaults', async () => {
  for (const field of ['maxAttempts', 'deadlineMs', 'retryDelayMs', 'maxBytes']) {
    let attempts = 0;
    await assert.rejects(readJson(ENDPOINT, decode, options(async () => { attempts++; return jsonResponse(); }, { [field]: null })), code('invalid_options'));
    assert.equal(attempts, 0);
  }
});
