declare module "cloudflare:workers" {
  export const env: Record<string, unknown>;
}

interface D1Result<T = unknown> { results: T[]; success?: boolean; meta?: Record<string, unknown>; }
interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<D1Result<T>>;
  run<T = Record<string, unknown>>(): Promise<D1Result<T>>;
}
interface D1Database {
  prepare(query: string): D1PreparedStatement;
  batch(statements: D1PreparedStatement[]): Promise<D1Result[]>;
}
interface R2ObjectBody { body: ReadableStream; }
interface R2Bucket {
  get(key: string): Promise<R2ObjectBody | null>;
  put(key: string, value: ReadableStream | ArrayBuffer | Blob, options?: Record<string, unknown>): Promise<unknown>;
}
interface Fetcher { fetch(request: Request): Promise<Response>; }
