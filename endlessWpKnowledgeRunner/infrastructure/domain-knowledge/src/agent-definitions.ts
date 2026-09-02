import type { AgentDefinition, AgentId } from '../../../packages/contracts/src/index.ts';

export const DOMAIN_KNOWLEDGE_AGENT_DEFINITIONS = [
  {
    agentId: 'orchestrator', nodeId: 'orchestrator', displayName: 'OrchestratorAgent',
    responsibility: '读取固化策略和执行摘要，形成当前轮的确定性任务计划。',
    basePrompt: 'Plan this knowledge-flywheel iteration. Preserve the fixed topology and delegate only the current node responsibilities.',
    inputContract: ['run policy', 'iteration', 'previous route summary'],
    outputContract: ['plan summary'], tools: [], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'doc-gen', nodeId: 'doc_gen', displayName: 'DocGenAgent',
    responsibility: '生成或按 Correction 增量修订知识正文，是知识正文的唯一自动执笔者。',
    basePrompt: 'Generate or revise the knowledge document from allowed source evidence. Keep claims concrete and traceable.',
    inputContract: ['source snapshot', 'worker fragments', 'previous knowledge and correction'],
    outputContract: ['schema-valid knowledge document'], tools: ['Read', 'Write', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'doc-worker', nodeId: 'doc_worker', displayName: 'DocWorkerAgent',
    responsibility: '按固定分块任务并行提取知识片段，不能发布或决定门禁。',
    basePrompt: 'Extract the assigned knowledge fragment from visible source evidence and preserve provenance.',
    inputContract: ['source partition', 'public interfaces'],
    outputContract: ['knowledge fragment'], tools: ['Read', 'Write', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'test-gen', nodeId: 'test_gen', displayName: 'TestGenAgent',
    responsibility: '从源码和公开接口提出候选行为测试，不读取候选知识。',
    basePrompt: 'Generate candidate behavior tests from source and public interfaces without reading generated knowledge.',
    inputContract: ['source snapshot', 'public interfaces'],
    outputContract: ['candidate test plan'], tools: ['Read', 'Write', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'code', nodeId: 'code', displayName: '代码生成角色（Code role）',
    responsibility: '由当前 Agent Provider 启动独立会话，仅依据候选知识和公开接口重新生成实现；这里的 code 是节点角色，不代表接入了独立的 CodeAgent CLI。',
    basePrompt: 'Generate a fresh implementation using only knowledge and public interfaces. Do not inspect reference source or gate answers. The trusted-context allowedGeneratedPaths list is the complete output allowlist: return implementation files only at those exact paths, and do not add tests, documentation, fixtures, or configuration files.',
    inputContract: ['candidate knowledge', 'public interfaces'],
    outputContract: ['generated project files'], tools: ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'check', nodeId: 'check', displayName: 'CheckAgent',
    responsibility: '只读检查生成实现、diff 和确定性判据，不能修改代码。',
    basePrompt: '只读检查提示上下文中内联的生成代码 Artifact 与确定性判据，不得修改实现。生成代码不会物化到你的公开接口工作区，不能把当前目录缺少生成文件当作缺陷。只报告由内联代码或证据直接支持的阻塞项。',
    inputContract: ['generated files', 'diff', 'criteria'],
    outputContract: ['structured check report'], tools: ['Read', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
  {
    agentId: 'review', nodeId: 'review', displayName: 'ReviewAgent',
    responsibility: '依据 Eval 和 Check 证据定位知识问题并提出可验证 Correction。',
    basePrompt: '依据内联的候选知识、结构化评测证据和 Check 报告做评审。生成代码位于调用方的不可变工件库，由 Evaluator 在独立副本中物化，不会出现在你的只读公开接口工作区；不得因当前目录缺文件而判失败。结构化评测证据是测试执行事实源：当评测通过且 Check 无阻塞时，除非内联证据存在可指出的具体矛盾，否则应建议 PASS；需要迭代时必须给出可复验的知识 Correction。',
    inputContract: ['knowledge', 'evaluation report', 'check report'],
    outputContract: ['structured review and correction'], tools: ['Read', 'Glob', 'Grep'], customizableFields: ['promptAddon'],
  },
] as const satisfies readonly AgentDefinition[];

const definitionMap = new Map<AgentId, AgentDefinition>(
  DOMAIN_KNOWLEDGE_AGENT_DEFINITIONS.map((definition) => [definition.agentId, definition]),
);

export function agentDefinition(agentId: AgentId): AgentDefinition {
  const definition = definitionMap.get(agentId);
  if (!definition) throw new Error(`Unknown fixed Agent: ${agentId}`);
  return definition;
}
