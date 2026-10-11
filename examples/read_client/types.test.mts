/** Compile-only checks. Never call this function or emit it into a public bundle. */
import { readJson } from './client.mjs';

async function checkInference(): Promise<void> {
  const value = await readJson('https://unit.invalid/data', (input: unknown) => {
    if (typeof input !== 'number') throw new Error('expected number');
    return input;
  });
  const valid: number = value;
  // @ts-expect-error A runtime decoder returning number must not infer string.
  const invalid: string = value;
  // @ts-expect-error Retry count must be numeric.
  await readJson('https://unit.invalid/data', (input) => input, { maxAttempts: '3' });
  void valid; void invalid;
}
void checkInference;

async function checkAsyncInference(): Promise<void> {
  const result = await readJson('https://unit.invalid/data', async () => ({ count: 7 }));
  const count: number = result.count;
  void count;
}
void checkAsyncInference;
