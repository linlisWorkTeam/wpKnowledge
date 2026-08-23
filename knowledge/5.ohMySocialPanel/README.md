# 5.ohMySocialPanel · ohMySocialPanel 调研

> 调研对象：[linlisWorkTeam/ohMySocialPanel](https://github.com/linlisWorkTeam/ohMySocialPanel)（副标题 *Agent For Social*）
> 调研日期：2026-08-23
> 调研方式：本地已有知识（3.workpanel / 4.workpanelConnecter / 1.dshAnalysis）+ 外部网络检索（web_search / GitHub API / 源码克隆）+
> 组织仓库快照：`ohMyWorkPanel`（Rust，v2.1.1）、`workpanelConnecter`（JavaScript）、`wpKnowledge`（Python）、`ohMySocialPanel`（空仓，仅 README "Agent For Social"，2 commit）

## 调研目标（用户四问 + 补充一问）

1. 市面上的娱乐类 AI 平台有哪些？它们基于什么形态、什么架构、什么理念、什么愿景？是否有市场？
2. 目前 AI 产品卖情绪价值的非常多——分析现在能用 AI 赚钱、且足够简单、足够搞笑的 TOP10 类型。
3. workpanel（ohMyWorkPanel / ohMySocialPanel 所在架构体系）能否作为底层架构，或作为"批量生成 AI 产品"的发动机？
4. 基于调研者视角，分析整体可行性。
5. （补充）ohMySocialPanel 是否适合做成 DSH（DeepSeek Harness）的插件？

## 目录

- [`调研/`](调研/)：核心调研报告
  - [01-娱乐类AI平台市场调研.md](调研/01-娱乐类AI平台市场调研.md) —— 市面娱乐类 AI 平台的形态/架构/理念/愿景与市场分析（子代理联网调研 + 本地视角导读）
  - [02-情绪价值AI产品TOP10.md](调研/02-情绪价值AI产品TOP10.md) —— 卖情绪价值、简单又搞笑的 AI 赚钱产品 TOP10（子代理联网调研 + 本地视角导读）
  - [03-workpanel架构与定位分析.md](调研/03-workpanel架构与定位分析.md) —— ohMySocialPanel/ohMyWorkPanel 架构事实、组织演进与定位推断
  - [04-workpanel作为产品发动机.md](调研/04-workpanel作为产品发动机.md) —— workpanel 能否作为底层架构/批量生成 AI 产品的发动机
  - [05-可行性分析.md](调研/05-可行性分析.md) —— 综合可行性判断（已按外部调研修订）
  - [06-DSH插件化可行性.md](调研/06-DSH插件化可行性.md) —— 能否做成 DSH 插件（补充问题）
- [`规划/`](规划/)：调研任务书与后续建议
- [`证据/`](证据/)：证据链（仓库快照、API 数据、源码位置）

## 一句话结论（先行版，详见各报告）

1. 娱乐类 AI 平台有真实且还在扩大的市场（全球 AI 情感陪伴下载 2.2 亿次、国内 CAGR 148.74%），形态从"聊天壳"向"内容+社交+游戏"复合形态演进，架构分层为 模型→Agent 运行时→平台层，理念从"工具"转向"情绪载体"；但已进入洗牌期，**纯 prompt 套壳窗口关闭，竞争转向 记忆/语音/IP/合规**。
2. 情绪价值 AI 产品中"简单而搞笑"的 TOP10：AI 塔罗/玄学（#1 百亿赛道+零门槛）、AI 毒舌/骂醒（#2 传播之王）、AI 声音克隆/变声（#3）、AI 语音陪伴+数字人（#4，监管风险最大）、AI 情书/恋爱键盘（#5）、AI 表情包/梗图（#6）、AI 哄睡/助眠（#7）、AI 写真/头像（#8，妙鸭警示）、AI 互动乙女（#9，重资产）、AI 整活内容号（#10）。**2026 年监管全量下架国内情感互动智能体——"简单搞笑"定位比"深度陪伴"更符合合规窗口。**
3. workpanel 架构（群聊即协作 + 多 Agent 调度 + 扩展宿主["业务不进平台仓"实证] + Connecter 联邦）满足"批量生成 AI 产品"发动机的形态要求，但它是**生产工具/协作平台**，不是**消费级娱乐产品**本身；作为发动机成立的前提是补齐"产品化外壳"（人格/皮肤/分发/计费）——即 ohMySocialPanel 的 *Agent For Social* 定位。
4. 可行性结论：**7/10，方向可行、时机可行**；最大风险不是技术而是"用生产工具做消费产品"的心智错位与获客分发；建议从 玄学/毒舌/表情包/整活 中选一个做"爆款验证"，代替"平台先行"。
5. DSH 插件化：**可行且有先例**（知识飞轮已是 DSH 动态插件），ohMySocialPanel 若做成 DSH 插件，可直接复用 agents/subagents/sessionPersistence/webServer/slots 等 Host/Client 能力；插件形态适合开发/内测期，大众消费产品仍需独立 Web/产品壳（DSH 当执行引擎）。

## 证据边界

- ohMySocialPanel 仓库当前为空（仅 README，2 commit），本调研对其定位采用"组织意图 + 命名 + 竞品格局"三角推断，标注为推断而非事实；但组织内已有**轨道 D 聊天群（groupKind=chat 已实现）**与 **AIHotel 剧本/NPC 扩展（灰度试运行）**作为社交形态的强旁证。
- 外部市场数据以 2026-08 检索快照为准（来源 URL 已标注在各报告），产品名单与数字会随时间变化；收入数字未经审计。
- DSH 能力取证基于本会话 Inspect Provider 实时目录（Host Service/Event/Builtin）。