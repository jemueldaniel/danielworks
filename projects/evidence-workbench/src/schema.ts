import {z} from 'zod';
export const Id=z.string().regex(/^[a-z][a-z0-9_-]{0,63}$/);
export const Engine=z.enum(['fts5','lexical']);
export const Submit=z.object({key:Id,engine:Engine,k:z.number().int().min(1).max(3)}).strict();
export const PageInput=z.object({cursor:Id.optional(),limit:z.number().int().min(1).max(20).optional()}).strict();
const Hash=z.string().regex(/^[0-9a-f]{64}$/);
const Score=z.number().min(0).max(1);
const Report=z.object({schema:z.literal('ranking-report.v1'),dataset_sha256:Hash,k:z.number().int().min(1).max(3),
  query_count:z.literal(5),macro_recall_at_k:Score,mrr_at_k:Score,
  queries:z.array(z.object({id:Id,recall_at_k:Score,reciprocal_rank_at_k:Score}).strict()).max(5),
  failures:z.array(z.object({id:Id,relevant:z.array(Id).max(6),retrieved:z.array(Id).max(3)}).strict()).max(5),
  input_digest:Hash,resumed_cases:z.number().int().min(0).max(5)}).strict();
export const Job=z.object({key:Id,state:z.enum(['pending','running','done','failed','cancelled']),engine:Engine,
  k:z.number().int().min(1).max(3),input_digest:Hash,generation:z.number().int().nonnegative(),
  attempts:z.number().int().min(0).max(3),checkpoint_count:z.number().int().min(0).max(5),result:Report.nullable()}).strict();
export const JobPage=z.object({items:z.array(Job).max(20),next_cursor:Id.nullable()}).strict();
export const Work=z.object({job:Job.nullable(),processed_cases:z.number().int().min(0).max(5)}).strict();
export const Cancel=z.object({cancelled:z.boolean()}).strict();
export const Dataset=z.object({version:z.literal('synthetic-v1'),sha256:Hash,document_count:z.literal(6),query_count:z.literal(5),
  engines:z.array(Engine),known_failure:z.literal('q-synonym'),synthetic:z.literal(true)}).strict();
export const SearchInput=z.object({query:z.string().min(1).max(500),k:z.number().int().min(1).max(3).default(2)}).strict();
export const Search=z.object({items:z.array(z.object({id:Id,text:z.string().max(1000),score:z.number()}).strict()).max(3)}).strict();
export type JobView=z.infer<typeof Job>;
export type SubmitInput=z.infer<typeof Submit>;
export type Profile='reader'|'operator'|'other-reader';
