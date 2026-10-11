/** Entirely synthetic transport: this demo makes no network request. */
import { readJson } from './client.mjs';

let attempts = 0;
const result = await readJson('https://unit.invalid/data', (input: unknown) => {
  if (input === null || typeof input !== 'object' || !('count' in input)
      || typeof input.count !== 'number' || !Number.isSafeInteger(input.count)) {
    throw new Error('expected an integer count');
  }
  return { count: input.count };
}, {
  retryDelayMs: 0,
  fetchImpl: async () => {
    attempts++;
    return new Response('{"count":7}', {
      status: attempts === 1 ? 503 : 200,
      headers: { 'content-type': 'application/json', 'retry-after': '0' },
    });
  },
});
console.log(JSON.stringify({ transport: 'synthetic', attempts, result }));
