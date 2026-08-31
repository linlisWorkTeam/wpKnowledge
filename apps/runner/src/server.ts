#!/usr/bin/env node
import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFileSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';
import { timingSafeEqual } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { createComposition } from './composition.ts';

const webRoot = join(dirname(fileURLToPath(import.meta.url)), '../web');
const assets = new Map([
  ['/', 'index.html'],
  ['/index.html', 'index.html'],
  ['/app.js', 'app.js'],
  ['/styles.css', 'styles.css'],
]);

function send(response: ServerResponse, status: number, body: unknown, contentType = 'application/json; charset=utf-8'): void {
  const bytes = Buffer.isBuffer(body)
    ? body
    : Buffer.from(typeof body === 'string' ? body : JSON.stringify(body), 'utf8');
  response.writeHead(status, {
    'content-type': contentType,
    'content-length': bytes.byteLength,
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
    'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'",
  });
  response.end(bytes);
}

function authorized(request: IncomingMessage, token: string | undefined): boolean {
  if (!token) return false;
  const supplied = request.headers.authorization?.replace(/^Bearer\s+/i, '') ?? '';
  const left = Buffer.from(supplied);
  const right = Buffer.from(token);
  return left.byteLength === right.byteLength && timingSafeEqual(left, right);
}

async function body(request: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const bytes = Buffer.from(chunk);
    size += bytes.byteLength;
    if (size > 1_048_576) throw new Error('PAYLOAD_TOO_LARGE');
    chunks.push(bytes);
  }
  const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('PAYLOAD_INVALID');
  return parsed as Record<string, unknown>;
}

export function createKnowledgeServer(input: {
  repositoryRoot?: string;
  runtimeDir?: string;
  writeToken?: string;
} = {}) {
  const composition = createComposition(input);
  const writeToken = input.writeToken ?? process.env.WP_KNOWLEDGE_WRITE_TOKEN;
  const server = createHttpServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://127.0.0.1');
    try {
      if (request.method === 'GET' && assets.has(url.pathname)) {
        const file = assets.get(url.pathname) as string;
        const bytes = readFileSync(join(webRoot, file));
        const contentType = extname(file) === '.html' ? 'text/html; charset=utf-8'
          : extname(file) === '.js' ? 'text/javascript; charset=utf-8'
          : 'text/css; charset=utf-8';
        send(response, 200, bytes, contentType);
        return;
      }
      if (request.method === 'GET' && url.pathname === '/favicon.ico') {
        response.writeHead(204, { 'cache-control': 'public, max-age=86400' });
        response.end();
        return;
      }
      if (request.method === 'GET' && url.pathname === '/health') {
        send(response, 200, { ok: true });
        return;
      }
      if (request.method === 'GET' && url.pathname === '/api/v1/status') {
        send(response, 200, composition.service.status());
        return;
      }
      if (request.method === 'GET' && url.pathname === '/api/v1/knowledge') {
        const statuses = (url.searchParams.get('status') ?? '').split(',').filter(Boolean);
        send(response, 200, { knowledge: composition.service.listKnowledgeVersions(statuses.length ? statuses : undefined) });
        return;
      }
      if (request.method === 'GET' && url.pathname.startsWith('/api/v1/knowledge/')) {
        const versionId = decodeURIComponent(url.pathname.slice('/api/v1/knowledge/'.length));
        const value = await composition.query.get(versionId);
        send(response, value ? 200 : 404, value ?? { error: 'NOT_FOUND' });
        return;
      }
      if (request.method === 'GET' && url.pathname === '/api/v1/query') {
        send(response, 200, await composition.query.search({
          query: url.searchParams.get('q') ?? '',
          top: Number(url.searchParams.get('top') ?? 8),
          statuses: (url.searchParams.get('status') ?? 'VERIFIED').split(',').filter(Boolean),
          category: url.searchParams.get('category') ?? undefined,
        }));
        return;
      }
      if (request.method === 'GET' && url.pathname === '/api/v1/scan') {
        send(response, 200, composition.scanner.scan(
          composition.config.acquisition.roots,
          composition.config.acquisition.maxCandidates,
        ));
        return;
      }
      if (request.method === 'POST' && url.pathname.startsWith('/api/v1/')) {
        if (!writeToken) {
          send(response, 503, { error: 'WRITE_API_DISABLED', message: 'Set WP_KNOWLEDGE_WRITE_TOKEN to enable mutations.' });
          return;
        }
        if (!authorized(request, writeToken)) {
          send(response, 401, { error: 'UNAUTHORIZED' });
          return;
        }
        const payload = await body(request);
        if (url.pathname === '/api/v1/ingest') {
          send(response, 201, await composition.service.ingestCandidate({
            moduleId: String(payload.moduleId ?? ''),
            body: String(payload.body ?? ''),
            title: String(payload.title ?? ''),
            description: String(payload.description ?? ''),
            category: String(payload.category ?? ''),
            tags: Array.isArray(payload.tags) ? payload.tags.map(String) : [],
            provenance: Array.isArray(payload.provenance) ? payload.provenance as never[] : [],
            metadata: payload.metadata && typeof payload.metadata === 'object' ? payload.metadata as Record<string, unknown> : {},
          }));
          return;
        }
        if (url.pathname === '/api/v1/feedback') {
          composition.service.recordFeedback(
            String(payload.versionId ?? ''), String(payload.action ?? ''),
            payload.rating === null || payload.rating === undefined ? null : Number(payload.rating),
            String(payload.note ?? ''),
          );
          send(response, 200, { ok: true });
          return;
        }
        if (url.pathname === '/api/v1/runs') {
          send(response, 201, composition.service.createRun(String(payload.moduleId ?? ''), String(payload.policyId ?? composition.config.publicationGate.policyId)));
          return;
        }
        if (url.pathname === '/api/v1/transition') {
          send(response, 200, composition.service.transition(String(payload.runId ?? ''), String(payload.state ?? '') as never));
          return;
        }
        if (url.pathname === '/api/v1/evaluate') {
          send(response, 201, await composition.service.recordEvaluation({
            runId: String(payload.runId ?? ''),
            versionId: String(payload.versionId ?? ''),
            evidenceRefs: Array.isArray(payload.evidenceRefs) ? payload.evidenceRefs as never[] : [],
            toolchainFingerprint: String(payload.toolchainFingerprint ?? ''),
            criticalFailures: Number(payload.criticalFailures ?? 0),
            testsPassed: Number(payload.testsPassed ?? 0),
            testsTotal: Number(payload.testsTotal ?? 0),
            stability: Number(payload.stability ?? 0),
            infrastructureFailure: Boolean(payload.infrastructureFailure),
          }, composition.config.publicationGate));
          return;
        }
        if (url.pathname === '/api/v1/publish') {
          send(response, 201, await composition.service.publish(
            String(payload.runId ?? ''), String(payload.versionId ?? ''), String(payload.decisionId ?? ''),
          ));
          return;
        }
      }
      send(response, 404, { error: 'NOT_FOUND' });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      send(response, message === 'PAYLOAD_TOO_LARGE' ? 413 : 400, { error: message });
    }
  });
  server.on('close', composition.close);
  return { server, composition };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const instance = createKnowledgeServer();
  instance.server.listen(instance.composition.config.server.port, instance.composition.config.server.host, () => {
    process.stdout.write(`wpKnowledge dashboard: http://${instance.composition.config.server.host}:${instance.composition.config.server.port}\n`);
  });
}
