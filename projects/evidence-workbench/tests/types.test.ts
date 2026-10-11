import {ApiClient} from '../src/api-client.js';
import type {SubmitInput} from '../src/schema.js';
const api=new ApiClient('http://127.0.0.1:8765/api/operator/');
const good:SubmitInput={key:'typed',engine:'fts5',k:2};
void (()=>api.submit(good));
// @ts-expect-error Engine names are a closed union.
const bad:SubmitInput={key:'typed',engine:'arbitrary-executable',k:2};
// @ts-expect-error No caller-selected tenant parameter.
void (()=>api.list({tenant:'other'}));
void bad;
