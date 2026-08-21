# 2026-08-21 WorkPanel 架构调研笔记

## Git 同步

- 远端：`https://github.com/linlisWorkTeam/workPanel.git`
- 最终：`master@c9cceff`，与 `origin/master` 一致，工作树干净。
- 版本：`package.json` 和 Cargo 均为 `2.0.0`。

## 验证

- Rust：123 passed，15 warnings。
- Vitest：23 files / 81 tests passed。
- `pnpm run build`：TypeScript 和 Vite production build 通过。

## 对比来源

- [Claude Code 文档](https://docs.anthropic.com/en/docs/claude-code)
- [OpenCode](https://github.com/anomalyco/opencode)
- [DeepSeek Harness](https://github.com/deepseek-ai/DeepSeek-Harness)
- [Clowder-ai](https://github.com/zts212653/clowder-ai)
- 本机 DSH 检出：`D:\AI\deepseek-harness\deepseek-harness`

## 后续应继续核实

1. 双实例情况下 scheduler 是否会重复 claim 同一个 run。
2. extension proxy 的所有入口是否统一经过群权限和认证。
3. API key 从 SQLite 迁移到 OS keychain 的兼容方案。
4. v2.0.0 之后 version pipeline、README、tag 和发布清单是否自动一致。
