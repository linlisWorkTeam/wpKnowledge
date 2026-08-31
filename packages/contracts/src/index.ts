import type {
  ArtifactRef, DomainEvent, EvaluationReport, FlywheelRun, GateDecision,
  KnowledgeVersion, ProvenanceRef,
} from '../../domain/src/index.ts';

export interface ArtifactStore {
  put(bytes: Uint8Array, mediaType: string): Promise<ArtifactRef>;
  get(ref: ArtifactRef): Promise<Uint8Array>;
  verify(ref: ArtifactRef): Promise<boolean>;
}

export interface CandidateInput {
  versionId: string;
  moduleId: string;
  parentVersionId: string | null;
  bodyRef: ArtifactRef;
  provenance: ProvenanceRef[];
  qualityOutcome: 'ACCEPTED' | 'REJECTED';
  qualityScore: number;
  title: string;
  description: string;
  category: string;
  tags: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface FlywheelRepository {
  initialize(): void;
  saveRun(run: FlywheelRun, event: DomainEvent): void;
  getRun(runId: string): FlywheelRun | null;
  updateRun(run: FlywheelRun, event: DomainEvent): void;
  saveCandidate(input: CandidateInput, event: DomainEvent): KnowledgeVersion;
  getKnowledgeVersion(versionId: string): KnowledgeVersion | null;
  findKnowledgeVersionByBody(moduleId: string, artifactId: string): KnowledgeVersion | null;
  latestKnowledgeVersion(moduleId: string): KnowledgeVersion | null;
  listKnowledgeVersions(statuses?: string[]): KnowledgeVersion[];
  saveEvaluationAndDecision(report: EvaluationReport, decision: GateDecision, event: DomainEvent): void;
  getGateDecision(decisionId: string): GateDecision | null;
  publish(
    publicationKey: string,
    run: FlywheelRun,
    version: KnowledgeVersion,
    decision: GateDecision,
    event: DomainEvent,
  ): { publicationKey: string; versionId: string; publishedAt: string; replayed: boolean };
  getPublication(publicationKey: string): { publicationKey: string; versionId: string; publishedAt: string } | null;
  recordFeedback(versionId: string, action: string, rating: number | null, note: string, now: string): void;
  listEvents(runId: string): DomainEvent[];
  getCheckpoint(generationKey: string): NodeCheckpoint | null;
  claimCheckpoint(checkpoint: NodeCheckpoint): NodeCheckpoint;
  commitCheckpoint(generationKey: string, outputRefs: ArtifactRef[], event: DomainEvent, now: string): NodeCheckpoint;
  failCheckpoint(generationKey: string, event: DomainEvent, now: string): NodeCheckpoint;
  status(): Record<string, unknown>;
}

export interface NodeCheckpoint {
  runId: string;
  nodeId: string;
  generationKey: string;
  status: 'RUNNING' | 'COMMITTED' | 'FAILED';
  inputRefs: ArtifactRef[];
  outputRefs: ArtifactRef[];
  retryCount: number;
  updatedAt: string;
}

export interface QualityReport {
  score: number;
  outcome: 'ACCEPTED' | 'REJECTED';
  signals: Record<string, number>;
  weakPoints: string[];
}

export interface QualityPolicy {
  evaluate(body: string, input: {
    title: string;
    description: string;
    provenance: ProvenanceRef[];
  }): QualityReport;
}

export interface AgentRequest {
  role: string;
  prompt: string;
  outputSchema: Record<string, unknown>;
  idempotencyKey: string;
  inputRefs?: ArtifactRef[];
}

export interface AgentProvider {
  run(request: AgentRequest, signal?: AbortSignal): Promise<Record<string, unknown>>;
}

export interface SandboxResult {
  exitCode: number;
  stdoutRef: ArtifactRef;
  stderrRef: ArtifactRef;
  timedOut: boolean;
  resourceUsage: Record<string, number>;
}

export interface Sandbox {
  execute(command: string, args: string[], inputRefs: ArtifactRef[], signal?: AbortSignal): Promise<SandboxResult>;
}

export interface LanguagePlugin {
  readonly languageId: string;
  compile(sourceRefs: ArtifactRef[], sandbox: Sandbox, signal?: AbortSignal): Promise<SandboxResult>;
  test(binaryRef: ArtifactRef, testRefs: ArtifactRef[], sandbox: Sandbox, signal?: AbortSignal): Promise<SandboxResult>;
}

export type ProjectTool = 'node' | 'pnpm' | 'cargo';

export interface ProjectCommand {
  tool: ProjectTool;
  args: string[];
  cwd?: string;
  repetitions?: number;
  timeoutMs?: number;
  maxOutputBytes?: number;
}

export interface GeneratedProjectFile {
  path: string;
  content: string;
}

export interface ProjectSnapshot {
  repositoryRoot: string;
  remote: string;
  checkoutHead: string;
  commit: string;
  dirty: boolean;
  sourcePaths: string[];
  publicInterfacePaths: string[];
  manifestRef: ArtifactRef;
}

export interface ProjectCommandResult {
  phase: 'prepare' | 'gate';
  tool: ProjectTool;
  args: string[];
  cwd: string;
  attempt: number;
  exitCode: number | null;
  timedOut: boolean;
  outputLimitExceeded: boolean;
  durationMs: number;
  stdout: string;
  stderr: string;
  testsPassed: number;
  testsTotal: number;
}

export interface ProjectEvaluation {
  label: string;
  commit: string;
  passed: boolean;
  testsPassed: number;
  testsTotal: number;
  stability: number;
  infrastructureFailure: boolean;
  toolchainFingerprint: string;
  generatedFileDigests: Record<string, string>;
  results: ProjectCommandResult[];
  evidenceRef: ArtifactRef;
}

export interface ProjectEvaluator {
  inspect(input: {
    repositoryRoot: string;
    expectedCommit?: string;
    sourcePaths: string[];
    publicInterfacePaths: string[];
  }): Promise<ProjectSnapshot>;
  evaluate(input: {
    label: string;
    snapshot: ProjectSnapshot;
    generatedFiles: GeneratedProjectFile[];
    prepareCommands: ProjectCommand[];
    commands: ProjectCommand[];
  }, signal?: AbortSignal): Promise<ProjectEvaluation>;
}
