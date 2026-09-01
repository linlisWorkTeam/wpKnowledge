# 贡献指南

感谢参与 wpKnowledge。这个仓库以 Spec 驱动、证据可追踪和目录边界稳定为基本协作约定。

## 开始之前

1. 先阅读根目录 [`README.md`](README.md)，确认当前能力和安全边界。
2. 根据改动类型阅读 [Spec 总入口](endlessWpKnowledgeRunner/specs/README.md)或[知识库目录](knowledge/知识库目录.md)。
3. 从最新默认分支创建独立分支，让一次 PR 只解决一个清晰问题。
4. 安装 Node.js 24+，执行 `npm ci`。

## 变更应放在哪里

| 变更 | 位置 |
| --- | --- |
| Knowledge Flywheel 代码、Web、测试、验收、Spec、运行文档 | `endlessWpKnowledgeRunner/` |
| 跨项目研究、证据、作者随笔和旧 OKF 输入 | `knowledge/` 对应编号域 |
| 历史 Python MVP 的考古性修复 | `mvp-flywheel/`，并明确说明为何不能在当前实现中完成 |
| 仓库级协作、CI、安全和首页 | 根目录文档或 `.github/` |

不要在根目录重新创建 `apps/`、`packages/`、`specs/`、`tests/`、`docs/`、`acceptance/` 或 `workpanel/`。更完整的归属规则见[仓库目录规则](endlessWpKnowledgeRunner/docs/REPOSITORY-GUIDE.md)。

## Spec 驱动的修改流程

### 行为或契约变更

1. 在 `endlessWpKnowledgeRunner/specs/` 找到对应需求、用例、工作流或 ADR。
2. 先补充可验收行为以及正常、失败和权限边界；新需求分配稳定的 `KF-SYS-*` ID。
3. 更新 `13-verification/traceability-matrix.md` 中的 Spec → 实现 → 测试映射。
4. 实现最小闭环，不引入平行状态机、Registry、Gate 或发布路径。
5. 增加对应层级的自动化测试，并同步用户/开发/运维文档。

### 纯文档或研究变更

- 事实结论要区分源码证据、运行证据和推断。
- 外部来源使用可核对链接；关键源码证据优先固定 commit。
- 不把计划写成已实现能力，也不把 deterministic fixture 写成 live-model 质量证明。
- 调整文件位置时修复所有相对链接，并运行完整文档契约测试。

## 本地验证

所有 PR 至少运行：

```bash
npm run typecheck
npm run validate:specs
npm test
```

按改动范围可追加：

```bash
npm run test:domain
npm run test:architecture
npm run test:integration
npm run test:acceptance
```

固定 commit 的 ohMyWorkPanel 验收需要本机已有对应源码对象，不属于每个贡献者都能运行的通用门禁。若未运行，请在 PR 中说明原因，不要伪造通过结果。测试层级和证据要求见[测试策略](endlessWpKnowledgeRunner/docs/TESTING.md)。

## Commit 与 Pull Request

Commit subject 建议使用简短前缀：

```text
feat: add workflow command endpoint
fix: reject mismatched evidence version
docs: add contributor onboarding
test: cover publication replay collision
refactor: isolate sqlite registry adapter
```

PR 描述应当包含：

- 动机和范围；
- 关联的需求、用例、ADR 或 Issue；
- 行为、数据和兼容性影响；
- 实际运行的命令及结果；
- 未验证内容和已知限制；
- 文档与追踪矩阵是否同步。

不要提交 `.workpanel/` 运行数据、密钥、Bearer token、外部 CLI 登录态、数据库、构建产物或临时验收工作区。AI Agent 生成的改动与人工改动遵循相同证据要求，提交者需要能够解释并维护最终内容。

## 评审标准

评审优先确认：

1. Spec、实现、测试和文档是否表达同一行为；
2. 是否保持领域核心、Application Port 和 Adapter 的依赖方向；
3. 是否保留独立评测、确定性 Gate 和原子发布的信任边界；
4. 失败、重试、幂等和恢复路径是否有证据；
5. PR 是否诚实陈述未运行或无法证明的部分。

安全问题不要在公开 Issue 中披露细节，请按 [`SECURITY.md`](SECURITY.md) 报告。

提交贡献即表示你同意该贡献按仓库的 [MIT License](LICENSE) 发布。
