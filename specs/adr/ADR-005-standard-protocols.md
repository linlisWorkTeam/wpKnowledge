# ADR-005：标准协议与 Adapter

- 状态：Accepted
- 日期：2026-08-31

## 决策

工具/知识互操作采用 MCP，Coding Agent PoC 采用 ACP，未来跨服务按需采用 A2A；业务通过 Adapter 使用，不创建私有传输协议。

## 后果

协议升级被隔离，减少自研；P0-B 必须验证实际 SDK 能力和错误映射，失败时可换 Adapter 而非污染核心。

