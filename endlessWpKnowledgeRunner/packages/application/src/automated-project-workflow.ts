import { readFileSync } from 'node:fs';
import { resolve, sep } from 'node:path';
import type {
  AgentId,
  GeneratedProjectFile,
  ProjectEvaluation,
  ProjectEvaluator,
  ProjectSnapshot,
  WorkflowStageExecutor,
  WorkflowStageInput,
  WorkflowStageResult,
  WorkflowEngine,
  WorkflowExecutionView,
  WorkflowHandle,
} from '../../contracts/src/index.ts';
import { assertInvariant, type ArtifactRef, type GateDecision } from '../../domain/src/index.ts';
import type { KnowledgeFlywheelService } from './index.ts';
import type { RealSourceScenario } from './project-flow.ts';
import { KNOWLEDGE_WRITING_GUIDE } from './knowledge-writing-guide.ts';

interface AutomatedAssets {
  knowledgeV1: string;
  knowledgeV2: string;
  codeV1: string;
  codeV2: string;
  correction: string;
  generatedPath: string;
  title: string;
  description: string;
}

export interface AutomatedProjectScenario extends RealSourceScenario {
  assets: AutomatedAssets;
}

interface DocumentOutput {
  body: string;
  title: string;
  description: string;
}

interface CodeOutput {
  files: GeneratedProjectFile[];
}

interface CheckOutput {
  blocking: boolean;
  findings: string[];
}

interface ReviewOutput {
  blocking: boolean;
  recommendation: 'PASS' | 'ITERATE';
  correction: Record<string, unknown> | null;
}

function contextKey(nodeId: string, iteration: number, workerId?: string): string {
  return `${nodeId}:${iteration}${workerId ? `:${workerId}` : ''}`;
}

function routeFor(outcome: GateDecision['outcome']): WorkflowStageResult['route'] {
  return outcome;
}

export class OhMyWorkPanelWorkflowExecutor implements WorkflowStageExecutor {
  readonly service: KnowledgeFlywheelService;
  readonly evaluator: ProjectEvaluator;
  readonly assetRoot: string;

  constructor(input: {
    service: KnowledgeFlywheelService;
    evaluator: ProjectEvaluator;
    assetRoot: string;
  }) {
    this.service = input.service;
    this.evaluator = input.evaluator;
    this.assetRoot = resolve(input.assetRoot);
  }

  async execute(input: WorkflowStageInput): Promise<WorkflowStageResult> {
    const scenario = input.context.scenario as AutomatedProjectScenario | undefined;
    if (!scenario || scenario.schemaVersion !== '1.0') throw new Error('WORKFLOW_SCENARIO_INVALID');
    switch (input.nodeId) {
      case 'orchestrator': return this.orchestrate(input, scenario);
      case 'doc_worker':
      case 'doc_gen':
      case 'test_gen':
      case 'code':
      case 'check':
      case 'review':
        return this.executeAgent(input, scenario, input.agentId as AgentId);
      case 'candidate_knowledge': return this.commitCandidate(input, scenario);
      case 'oracle_validation': return this.validateOracle(input, scenario);
      case 'evaluation': return this.evaluate(input, scenario);
      case 'workflow_router': return this.route(input);
      case 'rollback': return this.rollback(input);
      case 'publication': return this.publish(input);
      default: throw new Error(`WORKFLOW_STAGE_UNSUPPORTED: ${input.nodeId}`);
    }
  }

  private async orchestrate(
    input: WorkflowStageInput,
    scenario: AutomatedProjectScenario,
  ): Promise<WorkflowStageResult> {
    const current = this.service.repository.getRun(input.runId);
    if (!current) throw new Error(`WORKFLOW_RUN_NOT_FOUND: ${input.runId}`);
    if (current.state === 'CREATED') this.service.transition(input.runId, 'PLANNED');
    const planned = this.service.repository.getRun(input.runId);
    if (planned?.state === 'PLANNED' || planned?.state === 'ITERATING' || planned?.state === 'ROLLING_BACK') {
      this.service.transition(input.runId, 'GENERATING');
    }
    let snapshot = input.context.snapshot as ProjectSnapshot | undefined;
    let scenarioRef = input.context.scenarioRef as ArtifactRef | undefined;
    if (!snapshot) {
      snapshot = await this.evaluator.inspect({
        repositoryRoot: scenario.repositoryRoot,
        expectedCommit: scenario.expectedCommit,
        sourcePaths: scenario.sourcePaths,
        publicInterfacePaths: scenario.publicInterfacePaths,
      });
      scenarioRef = await this.service.artifacts.put(Buffer.from(JSON.stringify({
        ...scenario, repositoryRoot: snapshot.repositoryRoot, expectedCommit: snapshot.commit,
      }, null, 2)), 'application/json');
    }
    const agent = await this.commitAgentOutput(input, {
      strategy: 'fixed-knowledge-flywheel-v1',
      iteration: input.iteration,
      parallel: ['documentation', 'test-generation'],
    });
    return {
      detail: `planned iteration ${input.iteration}`,
      context: { snapshot, scenarioRef, [contextKey(input.nodeId, input.iteration)]: agent },
    };
  }

  private async executeAgent(
    input: WorkflowStageInput,
    scenario: AutomatedProjectScenario,
    agentId: AgentId,
  ): Promise<WorkflowStageResult> {
    let output: Record<string, unknown>;
    if (agentId === 'doc-gen') {
      output = {
        body: this.asset(input.iteration === 0 ? scenario.assets.knowledgeV1 : scenario.assets.knowledgeV2),
        title: scenario.assets.title,
        description: scenario.assets.description,
        writingGuide: KNOWLEDGE_WRITING_GUIDE,
      };
    } else if (agentId === 'code') {
      output = { files: [{
        path: scenario.assets.generatedPath,
        content: this.asset(input.iteration === 0 ? scenario.assets.codeV1 : scenario.assets.codeV2),
      }] };
    } else if (agentId === 'review') {
      const evaluationRef = input.context[contextKey('evaluationEvidenceRef', input.iteration)] as ArtifactRef | undefined;
      if (!evaluationRef) throw new Error('WORKFLOW_REVIEW_EVALUATION_MISSING');
      const evaluation = await this.readJson<ProjectEvaluation>(evaluationRef);
      output = {
        blocking: false,
        recommendation: evaluation.passed ? 'PASS' : 'ITERATE',
        correction: evaluation.passed
          ? null
          : JSON.parse(this.asset(scenario.assets.correction)) as Record<string, unknown>,
      };
    } else if (agentId === 'test-gen') {
      output = { candidateCommands: scenario.finalCommands, oracleRequired: true };
    } else if (agentId === 'check') {
      output = { blocking: false, findings: [], scope: scenario.allowedGeneratedPaths };
    } else if (agentId === 'doc-worker') {
      output = {
        workerId: input.workerId,
        fragment: `Source partition ${input.workerId ?? 'default'} prepared for DocGen.`,
        provenance: scenario.sourcePaths,
      };
    } else {
      output = { iteration: input.iteration, strategy: 'fixed-knowledge-flywheel-v1' };
    }
    const ref = await this.commitAgentOutput(input, output);
    return {
      detail: `${agentId} produced schema-bound fixture output`,
      context: { [contextKey(input.nodeId, input.iteration, input.workerId)]: ref },
    };
  }

  private async commitCandidate(
    input: WorkflowStageInput,
    scenario: AutomatedProjectScenario,
  ): Promise<WorkflowStageResult> {
    const documentRef = input.context[contextKey('doc_gen', input.iteration)] as ArtifactRef | undefined;
    if (!documentRef) throw new Error('WORKFLOW_DOC_OUTPUT_MISSING');
    const document = await this.readJson<DocumentOutput>(documentRef);
    const checkpoint = await this.service.executeNode({
      runId: input.runId,
      nodeId: input.nodeId,
      generationKey: `${input.runId}:${input.nodeId}:${input.iteration}`,
      inputRefs: [documentRef],
    }, async () => {
      const candidate = await this.service.ingestCandidate({
        moduleId: scenario.moduleId,
        body: document.body,
        title: document.title,
        description: document.description,
        category: 'automated-ohmyworkpanel',
        tags: ['ohmyworkpanel', 'langgraph'],
        provenance: scenario.sourcePaths.map((path) => ({
          path,
          commit: (input.context.snapshot as ProjectSnapshot).commit,
          pinned: true,
        })),
        metadata: { workflow: 'embedded-domain-knowledge', iteration: input.iteration },
      });
      if (candidate.quality.outcome !== 'ACCEPTED') throw new Error('WORKFLOW_CANDIDATE_QUALITY_REJECTED');
      return [candidate.version.bodyRef];
    });
    const bodyRef = checkpoint.outputRefs[0];
    if (!bodyRef) throw new Error('WORKFLOW_CANDIDATE_CHECKPOINT_EMPTY');
    const version = this.service.repository.findKnowledgeVersionByBody(scenario.moduleId, bodyRef.artifactId);
    if (!version) throw new Error('WORKFLOW_CANDIDATE_VERSION_MISSING');
    return {
      detail: `candidate ${version.versionId}`,
      context: {
        [contextKey('candidateVersionId', input.iteration)]: version.versionId,
        [contextKey('candidateBodyRef', input.iteration)]: bodyRef,
      },
    };
  }

  private async validateOracle(
    input: WorkflowStageInput,
    scenario: AutomatedProjectScenario,
  ): Promise<WorkflowStageResult> {
    const snapshot = input.context.snapshot as ProjectSnapshot;
    const scenarioRef = input.context.scenarioRef as ArtifactRef;
    const checkpoint = await this.service.executeNode({
      runId: input.runId,
      nodeId: input.nodeId,
      generationKey: `${input.runId}:${input.nodeId}:${input.iteration}`,
      inputRefs: [scenarioRef, snapshot.manifestRef],
    }, async () => {
      const evaluation = await this.evaluator.evaluate({
        label: `reference-oracle-${input.iteration}`,
        snapshot,
        generatedFiles: [],
        prepareCommands: scenario.prepareCommands,
        commands: scenario.referenceCommands,
      }, input.signal);
      if (!evaluation.passed) throw new Error(`REFERENCE_GATE_FAILED: ${evaluation.evidenceRef.artifactId}`);
      return [evaluation.evidenceRef];
    });
    return {
      detail: 'reference oracle passed',
      context: { [contextKey('oracleEvidenceRef', input.iteration)]: checkpoint.outputRefs[0] },
    };
  }

  private async evaluate(
    input: WorkflowStageInput,
    scenario: AutomatedProjectScenario,
  ): Promise<WorkflowStageResult> {
    const snapshot = input.context.snapshot as ProjectSnapshot;
    const scenarioRef = input.context.scenarioRef as ArtifactRef;
    const codeRef = input.context[contextKey('code', input.iteration)] as ArtifactRef | undefined;
    const bodyRef = input.context[contextKey('candidateBodyRef', input.iteration)] as ArtifactRef | undefined;
    const versionId = input.context[contextKey('candidateVersionId', input.iteration)];
    const checkRef = input.context[contextKey('check', input.iteration)] as ArtifactRef | undefined;
    const oracleRef = input.context[contextKey('oracleEvidenceRef', input.iteration)] as ArtifactRef | undefined;
    if (!codeRef || !bodyRef || !checkRef || !oracleRef || typeof versionId !== 'string') {
      throw new Error('WORKFLOW_EVALUATION_INPUT_MISSING');
    }
    const code = await this.readJson<CodeOutput>(codeRef);
    for (const file of code.files) {
      if (!scenario.allowedGeneratedPaths.includes(file.path)) throw new Error(`PROJECT_PATH_DENIED: ${file.path}`);
    }
    const checkpoint = await this.service.executeNode({
      runId: input.runId,
      nodeId: input.nodeId,
      generationKey: `${input.runId}:${input.nodeId}:${input.iteration}`,
      inputRefs: [scenarioRef, snapshot.manifestRef, bodyRef, codeRef, oracleRef, checkRef],
    }, async () => {
      const evaluation = await this.evaluator.evaluate({
        label: `generated-iteration-${input.iteration}`,
        snapshot,
        generatedFiles: code.files,
        prepareCommands: scenario.prepareCommands,
        commands: input.iteration === 0 ? scenario.firstIterationCommands : scenario.finalCommands,
      }, input.signal);
      return [evaluation.evidenceRef];
    });
    const evidenceRef = checkpoint.outputRefs[0];
    if (!evidenceRef) throw new Error('WORKFLOW_EVALUATION_EVIDENCE_MISSING');
    const evaluation = await this.readJson<ProjectEvaluation>(evidenceRef);
    const run = this.service.repository.getRun(input.runId);
    if (run?.state === 'GENERATING') this.service.transition(input.runId, 'EVALUATING');
    if (evaluation.infrastructureFailure) {
      const decision = await this.recordGateDecision(input, evaluation);
      return {
        detail: `evaluation infrastructure failed; gate ${decision.outcome}`,
        context: {
          [contextKey('evaluationEvidenceRef', input.iteration)]: evidenceRef,
          [contextKey('gateDecision', input.iteration)]: decision,
        },
        route: routeFor(decision.outcome),
      };
    }
    return {
      detail: `evaluation ${evaluation.passed ? 'passed' : 'failed'}; awaiting review and gate`,
      context: { [contextKey('evaluationEvidenceRef', input.iteration)]: evidenceRef },
    };
  }

  private async route(input: WorkflowStageInput): Promise<WorkflowStageResult> {
    const existing = input.context[contextKey('gateDecision', input.iteration)] as GateDecision | undefined;
    const evaluationRef = input.context[contextKey('evaluationEvidenceRef', input.iteration)] as ArtifactRef | undefined;
    if (!evaluationRef) throw new Error('WORKFLOW_EVALUATION_EVIDENCE_MISSING');
    const evaluation = await this.readJson<ProjectEvaluation>(evaluationRef);
    const decision = existing ?? await this.recordGateDecision(input, evaluation);
    const route = routeFor(decision.outcome);
    const run = this.service.repository.getRun(input.runId);
    if (route === 'ITERATE' && run?.state === 'REVIEWING') {
      this.service.transition(input.runId, 'ITERATING');
    } else if (route === 'ROLLBACK' && run?.state === 'REVIEWING') {
      this.service.transition(input.runId, 'ROLLING_BACK');
    } else if (route === 'STOPPED' && run?.state === 'REVIEWING') {
      this.service.transition(input.runId, 'LOW_CONFIDENCE');
    }
    return {
      detail: `workflow route ${route}`,
      route,
      context: { [contextKey('gateDecision', input.iteration)]: decision },
    };
  }

  private async recordGateDecision(
    input: WorkflowStageInput,
    evaluation: ProjectEvaluation,
  ): Promise<GateDecision> {
    const snapshot = input.context.snapshot as ProjectSnapshot;
    const scenarioRef = input.context.scenarioRef as ArtifactRef;
    const bodyRef = input.context[contextKey('candidateBodyRef', input.iteration)] as ArtifactRef | undefined;
    const codeRef = input.context[contextKey('code', input.iteration)] as ArtifactRef | undefined;
    const checkRef = input.context[contextKey('check', input.iteration)] as ArtifactRef | undefined;
    const oracleRef = input.context[contextKey('oracleEvidenceRef', input.iteration)] as ArtifactRef | undefined;
    const reviewRef = input.context[contextKey('review', input.iteration)] as ArtifactRef | undefined;
    const versionId = input.context[contextKey('candidateVersionId', input.iteration)];
    if (!bodyRef || !codeRef || !checkRef || !oracleRef || typeof versionId !== 'string') {
      throw new Error('WORKFLOW_GATE_INPUT_MISSING');
    }
    const check = await this.readJson<CheckOutput>(checkRef);
    const review = reviewRef ? await this.readJson<ReviewOutput>(reviewRef) : null;
    const evaluationRef = input.context[contextKey('evaluationEvidenceRef', input.iteration)] as ArtifactRef | undefined;
    if (!evaluationRef) throw new Error('WORKFLOW_EVALUATION_EVIDENCE_MISSING');
    const inputRefs = [scenarioRef, snapshot.manifestRef, bodyRef, codeRef, oracleRef, checkRef];
    if (reviewRef) inputRefs.push(reviewRef);
    const { decision } = await this.service.recordEvaluation({
      runId: input.runId,
      versionId,
      inputRefs,
      evidenceRefs: [evaluationRef],
      toolchainFingerprint: evaluation.toolchainFingerprint,
      criticalFailures: evaluation.passed ? 0 : 1,
      testsPassed: evaluation.testsPassed,
      testsTotal: evaluation.testsTotal,
      stability: evaluation.stability,
      infrastructureFailure: evaluation.infrastructureFailure,
      checkBlocking: check.blocking,
      reviewBlocking: review?.blocking ?? false,
    }, {
      policyId: this.service.repository.getRun(input.runId)?.policyId ?? 'local-v1',
      minimumStability: 1,
      requireAllTests: true,
      maxIterations: input.maxIterations,
    });
    return decision;
  }

  private async rollback(input: WorkflowStageInput): Promise<WorkflowStageResult> {
    const run = this.service.repository.getRun(input.runId);
    return {
      detail: run?.bestVersionId ? `requested rollback to ${run.bestVersionId}` : 'rollback requested without historical best',
    };
  }

  private async publish(input: WorkflowStageInput): Promise<WorkflowStageResult> {
    const decision = input.context[contextKey('gateDecision', input.iteration)] as GateDecision | undefined;
    const versionId = input.context[contextKey('candidateVersionId', input.iteration)];
    if (!decision || typeof versionId !== 'string') throw new Error('WORKFLOW_PUBLICATION_INPUT_MISSING');
    const publication = await this.service.publish(input.runId, versionId, decision.decisionId);
    return {
      detail: `wpKnowledge publication ${publication.publicationKey}`,
      context: { publication },
      route: 'PASS',
    };
  }

  private async commitAgentOutput(input: WorkflowStageInput, output: Record<string, unknown>): Promise<ArtifactRef> {
    const inputRefs = Object.values(input.context)
      .filter((value): value is ArtifactRef => Boolean(
        value && typeof value === 'object' && 'artifactId' in value && 'sha256' in value,
      ));
    const checkpoint = await this.service.executeNode({
      runId: input.runId,
      nodeId: input.workerId ? `${input.nodeId}:${input.workerId}` : input.nodeId,
      generationKey: `${input.runId}:${input.nodeId}:${input.iteration}:${input.workerId ?? 'main'}`,
      inputRefs,
    }, async () => [await this.service.artifacts.put(
      Buffer.from(JSON.stringify(output, null, 2)), 'application/json',
    )]);
    const ref = checkpoint.outputRefs[0];
    if (!ref) throw new Error(`WORKFLOW_AGENT_OUTPUT_MISSING: ${input.nodeId}`);
    return ref;
  }

  private asset(relativePath: string): string {
    const target = resolve(this.assetRoot, relativePath);
    if (target !== this.assetRoot && !target.startsWith(`${this.assetRoot}${sep}`)) {
      throw new Error(`WORKFLOW_ASSET_DENIED: ${relativePath}`);
    }
    return readFileSync(target, 'utf8');
  }

  private async readJson<T>(ref: ArtifactRef): Promise<T> {
    return JSON.parse(Buffer.from(await this.service.artifacts.get(ref)).toString('utf8')) as T;
  }
}

export class AutomatedProjectWorkflowService {
  readonly flywheel: KnowledgeFlywheelService;
  readonly workflow: WorkflowEngine;

  constructor(flywheel: KnowledgeFlywheelService, workflow: WorkflowEngine) {
    this.flywheel = flywheel;
    this.workflow = workflow;
  }

  async start(
    scenario: AutomatedProjectScenario,
    input: { policyId: string; maxIterations: number; workerCount?: number },
  ): Promise<WorkflowHandle> {
    assertInvariant(Number.isSafeInteger(input.maxIterations) && input.maxIterations >= 1,
      'workflow maxIterations must be a positive integer');
    assertInvariant(Number.isSafeInteger(input.workerCount ?? 1) && (input.workerCount ?? 1) >= 0 && (input.workerCount ?? 1) <= 5,
      'workflow workerCount must be an integer from 0 to 5');
    const run = this.flywheel.createRun(scenario.moduleId, input.policyId);
    this.flywheel.transition(run.runId, 'PLANNED');
    return this.workflow.start({
      runId: run.runId,
      maxIterations: input.maxIterations,
      workerCount: input.workerCount ?? 1,
      context: { scenario },
    });
  }

  async wait(runId: string): Promise<WorkflowExecutionView> {
    try {
      const view = await this.workflow.wait(runId);
      this.synchronizeTerminalRun(runId, view.executionStatus);
      return view;
    } catch (error) {
      this.synchronizeTerminalRun(runId, 'FAILED');
      throw error;
    }
  }

  status(runId: string): Promise<WorkflowExecutionView> {
    return this.workflow.status(runId);
  }

  resume(runId: string): Promise<WorkflowHandle> {
    return this.workflow.resume(runId);
  }

  async cancel(runId: string): Promise<void> {
    await this.workflow.cancel(runId);
    this.synchronizeTerminalRun(runId, 'CANCELLED');
  }

  private synchronizeTerminalRun(
    runId: string,
    status: WorkflowExecutionView['executionStatus'],
  ): void {
    const next = status === 'FAILED' ? 'FAILED' : status === 'CANCELLED' ? 'CANCELLED' : null;
    if (!next) return;
    const run = this.flywheel.repository.getRun(runId);
    if (run && !['VERIFIED', 'LOW_CONFIDENCE', 'FAILED', 'CANCELLED'].includes(run.state)) {
      this.flywheel.transition(runId, next);
    }
  }
}
