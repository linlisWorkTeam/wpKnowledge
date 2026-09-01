import { readFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  DeterministicQualityPolicy, KnowledgeFlywheelService, KnowledgeQueryService,
} from '../../../packages/application/src/index.ts';
import {
  LocalCasArtifactStore, SQLiteFlywheelRepository,
} from '../../../packages/adapters/sqlite-cas/src/index.ts';
import { SourceScanner } from '../../../packages/adapters/source-scan/src/index.ts';

export interface WorkpanelConfig {
  schemaVersion: '1.0';
  runtimeDir: string;
  qualityGate: { threshold: number };
  publicationGate: {
    policyId: string;
    minimumStability: number;
    requireAllTests: boolean;
    maxIterations: number;
  };
  server: { host: string; port: number };
  acquisition: { roots: string[]; maxCandidates: number };
  legacy: { knowledgeDir: string };
}

const moduleDirectory = dirname(fileURLToPath(import.meta.url));
export const componentRoot = resolve(moduleDirectory, '../../..');
export const defaultRepositoryRoot = resolve(componentRoot, '..');

export function loadWorkpanelConfig(repositoryRoot = defaultRepositoryRoot): WorkpanelConfig {
  const configPath = process.env.WP_FLYWHEEL_CONFIG
    || (repositoryRoot === defaultRepositoryRoot
      ? join(componentRoot, 'runner.config.json')
      : join(repositoryRoot, 'endlessWpKnowledgeRunner', 'runner.config.json'));
  const config = JSON.parse(readFileSync(configPath, 'utf8')) as WorkpanelConfig;
  if (config.schemaVersion !== '1.0') throw new Error(`CONFIG_INVALID: unsupported schemaVersion ${config.schemaVersion}`);
  if (!Number.isFinite(config.qualityGate?.threshold) || config.qualityGate.threshold < 0 || config.qualityGate.threshold > 100) {
    throw new Error('CONFIG_INVALID: qualityGate.threshold must be 0..100');
  }
  if (!config.publicationGate?.policyId) throw new Error('CONFIG_INVALID: publicationGate.policyId is required');
  if (config.publicationGate.minimumStability < 0 || config.publicationGate.minimumStability > 1) {
    throw new Error('CONFIG_INVALID: publicationGate.minimumStability must be 0..1');
  }
  if (!Number.isSafeInteger(config.publicationGate.maxIterations) || config.publicationGate.maxIterations < 0) {
    throw new Error('CONFIG_INVALID: publicationGate.maxIterations must be a non-negative integer');
  }
  if (!Number.isSafeInteger(config.server?.port) || config.server.port < 1 || config.server.port > 65535) {
    throw new Error('CONFIG_INVALID: server.port must be 1..65535');
  }
  if (!Array.isArray(config.acquisition?.roots) || !config.acquisition.roots.every((root) => typeof root === 'string')) {
    throw new Error('CONFIG_INVALID: acquisition.roots must be an array of paths');
  }
  if (!Number.isSafeInteger(config.acquisition.maxCandidates) || config.acquisition.maxCandidates < 1) {
    throw new Error('CONFIG_INVALID: acquisition.maxCandidates must be a positive integer');
  }
  return config;
}

export function createComposition(input: {
  repositoryRoot?: string;
  runtimeDir?: string;
  clock?: () => string;
} = {}) {
  const repositoryRoot = resolve(input.repositoryRoot ?? defaultRepositoryRoot);
  const config = loadWorkpanelConfig(repositoryRoot);
  const configuredRuntime = input.runtimeDir ?? process.env.WP_FLYWHEEL_HOME ?? config.runtimeDir;
  const runtimeDir = isAbsolute(configuredRuntime) ? configuredRuntime : join(repositoryRoot, configuredRuntime);
  const artifacts = new LocalCasArtifactStore(join(runtimeDir, 'cas'));
  const repository = new SQLiteFlywheelRepository(join(runtimeDir, 'registry.sqlite'));
  const service = new KnowledgeFlywheelService({
    artifacts,
    repository,
    qualityPolicy: new DeterministicQualityPolicy(config.qualityGate.threshold),
    clock: input.clock,
  });
  const query = new KnowledgeQueryService(artifacts, repository);
  const scanner = new SourceScanner(repositoryRoot, repository);
  return {
    repositoryRoot,
    runtimeDir,
    config,
    artifacts,
    repository,
    service,
    query,
    scanner,
    close: () => repository.close(),
  };
}
