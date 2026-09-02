import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { realpathSync } from 'node:fs';
import { resolve } from 'node:path';
import Ajv2020Import from 'ajv/dist/2020.js';
import type { AgentProvider, AgentRequest } from '../../../contracts/src/index.ts';

const Ajv2020 = Ajv2020Import as unknown as new (options: Record<string, unknown>) => {
  compile(schema: Record<string, unknown>): {
    (value: unknown): boolean;
    errors?: unknown;
  };
  errorsText(errors: unknown): string;
};

export interface DeepSeekHarnessAuditRecord {
  schemaVersion: '1.0';
  provider: 'deepseek-harness-headless';
  role: string;
  idempotencyKey: string;
  workspaceRoot: string;
  promptSha256: string;
  schemaSha256: string;
  startedAt: string;
  completedAt: string;
  durationMs: number;
  exitCode: number | null;
  timedOut: boolean;
  cancelled: boolean;
  stdoutBytes: number;
  stderrBytes: number;
  status: 'SUCCEEDED' | 'FAILED';
  errorCode: string | null;
  metadata: Record<string, string | number | boolean | null>;
}

export interface DeepSeekHarnessAgentOptions {
  command?: string;
  args?: string[];
  env?: NodeJS.ProcessEnv;
  timeoutMs?: number;
  maxOutputBytes?: number;
  allowedWorkspaceRoots: string[];
  clock?: () => Date;
  onAudit?: (record: DeepSeekHarnessAuditRecord) => void | Promise<void>;
}

function digest(value: string): string {
  return createHash('sha256').update(value).digest('hex');
}

function extractJsonCandidates(stdout: string): Record<string, unknown>[] {
  const trimmed = stdout.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i)?.[1]?.trim();
  const texts = [fenced, trimmed].filter((value): value is string => Boolean(value));
  let depth = 0;
  let start = -1;
  let quoted = false;
  let escaped = false;
  for (let index = 0; index < trimmed.length; index += 1) {
    const character = trimmed[index];
    if (depth === 0) {
      // DSH may print diagnostics before the final answer. Quotes in those lines
      // are not JSON string delimiters and must not poison the object scanner.
      if (character === '{') {
        start = index;
        depth = 1;
        quoted = false;
        escaped = false;
      }
      continue;
    }
    if (quoted) {
      if (escaped) escaped = false;
      else if (character === '\\') escaped = true;
      else if (character === '"') quoted = false;
      continue;
    }
    if (character === '"') {
      quoted = true;
      continue;
    }
    if (character === '{') {
      depth += 1;
    } else if (character === '}' && depth > 0) {
      depth -= 1;
      if (depth === 0 && start >= 0) {
        texts.push(trimmed.slice(start, index + 1));
        start = -1;
      }
    }
  }
  const outputs: Record<string, unknown>[] = [];
  const seen = new Set<string>();
  for (const candidate of texts) {
    try {
      const parsed = JSON.parse(candidate) as unknown;
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        const canonical = JSON.stringify(parsed);
        if (!seen.has(canonical)) {
          seen.add(canonical);
          outputs.push(parsed as Record<string, unknown>);
        }
      }
    } catch {
      // Report one stable error below without reflecting model output.
    }
  }
  return outputs;
}

function canonicalWorkspace(requested: string, allowedRoots: string[]): string {
  const workspace = realpathSync(resolve(requested));
  const allowed = allowedRoots.map((root) => realpathSync(resolve(root)));
  if (!allowed.some((root) => workspace === root || workspace.startsWith(`${root}/`))) {
    throw new Error('DSH_AGENT_WORKSPACE_DENIED');
  }
  return workspace;
}

function providerPrompt(request: AgentRequest): string {
  const properties = request.outputSchema.properties;
  const allowedKeys = properties && typeof properties === 'object'
    ? Object.keys(properties as Record<string, unknown>)
    : [];
  return [
    `你是知识飞轮中的 ${request.role} 节点。`,
    request.prompt,
    '必须只输出一个 JSON 对象，不要使用 Markdown 代码块，不要补充解释。',
    ...(allowedKeys.length > 0
      ? [`顶层键必须恰好是：${allowedKeys.join('、')}。不得添加 schema note、metadata、additionalProperties 或其他字段。`]
      : []),
    '输出必须严格符合下面的 JSON Schema：',
    JSON.stringify(request.outputSchema),
    `幂等键：${request.idempotencyKey}`,
  ].join('\n\n');
}

export class DeepSeekHarnessHeadlessAgent implements AgentProvider {
  readonly command: string;
  readonly args: string[];
  readonly env: NodeJS.ProcessEnv;
  readonly timeoutMs: number;
  readonly maxOutputBytes: number;
  readonly allowedWorkspaceRoots: string[];
  readonly clock: () => Date;
  readonly onAudit?: DeepSeekHarnessAgentOptions['onAudit'];

  constructor(options: DeepSeekHarnessAgentOptions) {
    if (options.allowedWorkspaceRoots.length === 0) throw new Error('DSH_AGENT_ALLOWED_ROOT_REQUIRED');
    this.command = options.command ?? 'dsh';
    this.args = options.args ?? ['--profile', 'headless'];
    this.env = { ...process.env, DSH_TELEMETRY_MODE: 'DISABLED', ...options.env };
    this.timeoutMs = options.timeoutMs ?? 300_000;
    this.maxOutputBytes = options.maxOutputBytes ?? 2 * 1024 * 1024;
    this.allowedWorkspaceRoots = [...options.allowedWorkspaceRoots];
    this.clock = options.clock ?? (() => new Date());
    this.onAudit = options.onAudit;
  }

  async run(request: AgentRequest, signal?: AbortSignal): Promise<Record<string, unknown>> {
    if (!request.workspaceRoot) throw new Error('DSH_AGENT_WORKSPACE_REQUIRED');
    if (signal?.aborted) throw new Error('AGENT_CANCELLED');
    const workspaceRoot = canonicalWorkspace(request.workspaceRoot, this.allowedWorkspaceRoots);
    const prompt = providerPrompt(request);
    const started = this.clock();
    let exitCode: number | null = null;
    let timedOut = false;
    let cancelled = false;
    let stdoutBytes = 0;
    let stderrBytes = 0;
    let errorCode: string | null = null;
    try {
      const stdout = await new Promise<string>((resolveOutput, reject) => {
        const child = spawn(this.command, [...this.args, prompt], {
          cwd: workspaceRoot,
          env: this.env,
          shell: false,
          stdio: ['ignore', 'pipe', 'pipe'],
          windowsHide: true,
        });
        const stdoutChunks: Buffer[] = [];
        const stderrChunks: Buffer[] = [];
        let settled = false;
        const terminate = () => {
          if (!child.killed) child.kill('SIGTERM');
          const killTimer = setTimeout(() => {
            if (!child.killed) child.kill('SIGKILL');
          }, 2_000);
          killTimer.unref();
        };
        const timeout = setTimeout(() => {
          timedOut = true;
          terminate();
        }, this.timeoutMs);
        timeout.unref();
        const abort = () => {
          cancelled = true;
          terminate();
        };
        signal?.addEventListener('abort', abort, { once: true });
        const collect = (target: Buffer[], chunk: Buffer, stream: 'stdout' | 'stderr') => {
          if (settled) return;
          if (stream === 'stdout') stdoutBytes += chunk.byteLength;
          else stderrBytes += chunk.byteLength;
          if (stdoutBytes + stderrBytes > this.maxOutputBytes) {
            settled = true;
            terminate();
            reject(new Error('DSH_AGENT_OUTPUT_LIMIT_EXCEEDED'));
            return;
          }
          target.push(chunk);
        };
        child.stdout.on('data', (chunk: Buffer) => collect(stdoutChunks, chunk, 'stdout'));
        child.stderr.on('data', (chunk: Buffer) => collect(stderrChunks, chunk, 'stderr'));
        child.on('error', (error) => {
          if (settled) return;
          settled = true;
          reject(new Error(`DSH_AGENT_SPAWN_FAILED: ${(error as NodeJS.ErrnoException).code ?? 'UNKNOWN'}`));
        });
        child.on('close', (code) => {
          exitCode = code;
          clearTimeout(timeout);
          signal?.removeEventListener('abort', abort);
          if (settled) return;
          settled = true;
          if (cancelled) reject(new Error('AGENT_CANCELLED'));
          else if (timedOut) reject(new Error('DSH_AGENT_TIMEOUT'));
          else if (code !== 0) reject(new Error('DSH_AGENT_PROCESS_FAILED'));
          else resolveOutput(Buffer.concat(stdoutChunks).toString('utf8'));
        });
      });
      const ajv = new Ajv2020({ allErrors: true, strict: true });
      const validate = ajv.compile(request.outputSchema);
      const candidates = extractJsonCandidates(stdout);
      if (candidates.length === 0) throw new Error('DSH_AGENT_OUTPUT_NOT_JSON');
      const output = [...candidates].reverse().find((candidate) => validate(candidate));
      if (!output) {
        validate(candidates.at(-1));
        throw new Error(`AGENT_OUTPUT_INVALID: ${ajv.errorsText(validate.errors)}`);
      }
      await this.audit(request, workspaceRoot, prompt, started, {
        exitCode, timedOut, cancelled, stdoutBytes, stderrBytes, status: 'SUCCEEDED', errorCode: null,
      });
      return output;
    } catch (error) {
      errorCode = error instanceof Error ? error.message.split(':', 1)[0] ?? 'DSH_AGENT_FAILED' : 'DSH_AGENT_FAILED';
      await this.audit(request, workspaceRoot, prompt, started, {
        exitCode, timedOut, cancelled, stdoutBytes, stderrBytes, status: 'FAILED', errorCode,
      });
      throw error;
    }
  }

  private async audit(
    request: AgentRequest,
    workspaceRoot: string,
    prompt: string,
    started: Date,
    outcome: Pick<DeepSeekHarnessAuditRecord,
      'exitCode' | 'timedOut' | 'cancelled' | 'stdoutBytes' | 'stderrBytes' | 'status' | 'errorCode'>,
  ): Promise<void> {
    if (!this.onAudit) return;
    const completed = this.clock();
    await this.onAudit({
      schemaVersion: '1.0', provider: 'deepseek-harness-headless', role: request.role,
      idempotencyKey: request.idempotencyKey, workspaceRoot,
      promptSha256: digest(prompt), schemaSha256: digest(JSON.stringify(request.outputSchema)),
      startedAt: started.toISOString(), completedAt: completed.toISOString(),
      durationMs: Math.max(0, completed.getTime() - started.getTime()),
      ...outcome,
      metadata: { ...(request.metadata ?? {}) },
    });
  }
}
