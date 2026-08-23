---
date: 2026-08-23
topic: ohMyWorkPanel frontend style consistency
status: active
---

# ohMyWorkPanel 前台风格一致性评估

## 研究对象

`D:\AI\LinlisWorkPanel` 当前工作区，基线 commit `7045033`；工作区同时存在未提交的前台、构建和后端修改，本报告只做读取分析，不覆盖这些修改。

## 结论

DeepSeek 的诊断方向基本正确，但不能把“扫描到的颜色字面量数量”直接当成全部缺陷，也不建议立刻用正则扫描把所有 hex/rgb 都设为错误。

当前不一致的主要来源是三条样式管线同时存在：

1. `src/shell/tokens.css` 提供主题原始值和主壳基础 token。
2. `src/themes.css` 提供 `--lp-*` 语义别名、主题覆盖和大量新壳样式。
3. `src/styles.css` 仍保留旧页面的大量固定颜色、fallback 色值和旧控件样式。

入口 `src/main.tsx` 依次加载 `tokens.css`、`styles.css`、`themes.css`。这使主壳可以跟随 `--lp-*` 换肤，但旧页面、弹窗、表单、PM/工作流页面和某些内联样式仍可能走旧颜色或自己的局部规则。

## 证据

- `src/main.tsx:5-8` 同时加载 `tokens.css`、`styles.css`、`themes.css`。
- `src/shell/tokens.css:16-114` 定义七套主题的 `--bg/--surf/--elev/--ink/--dim/--acc/--line/--user` 等原始值。
- `src/themes.css:2-9` 先定义一组 `--lp-*` 别名，后续主题区块又重复定义 `--lp-*`，说明语义层已经存在但仍未收敛为单一映射入口。
- `src/styles.css:1-14` 仍包含 `#202a3a`、`#fff`、`#dbe2eb`、`#4b93df` 等旧页面固定颜色；同时存在 `var(--token, #fallback)` 形式的颜色 fallback。
- `src/App.tsx:1973` 的 `Modal` 只是 `modal-backdrop` + `section.modal` 的局部函数，不是可复用的基础组件契约。
- `src/components/ContextActionMenu.tsx:114` 已有独立的上下文菜单组件，但其视觉契约仍由 `.ctx-menu` 样式承担，菜单颜色仍可见 `#1a1a1a`、`rgba(...)` 等非语义值。
- `src/components/ui/index.ts` 当前主要导出 `Divider` 和 `useAppFrame`，尚未形成 Modal、Button、FormField、Popover 等基础 UI 入口。
- `src/theme.tsx:26-70` 的主题色板是主题定义本身，不能与业务组件中的硬编码颜色等价处理；这些字面量应保留在主题源文件白名单内。

因此，DeepSeek 给出的“存在双变量体系、旧页面硬编码、PmPanel 内联色值”属于有效风险提示；但具体的“214 个变量、642 行、37 处”需要固定扫描口径后再作为指标使用，不能直接当作本次评估的精确事实。

## 推荐目标架构

### 1. 只保留一个消费层

建议把 `--lp-*` 定为组件消费层的唯一命名空间，主题文件只负责给它赋值。原始主题值可以继续存在，但只允许出现在主题定义区：

```text
主题源值（仅 themes/tokens 定义区）
        ↓
--lp-* 语义 token（唯一组件消费层）
        ↓
组件 CSS / 页面 CSS / Modal / Menu / Toast
```

不要让业务组件同时直接消费 `--bg`、`--elev`、`--ink`、`--text`、`--border` 和 `--lp-*`。旧变量可以保留一个过渡周期，但应集中在一个 compatibility block 中映射，不能在每个主题区块重复散落映射。

第一批建议固定的语义 token：

```text
背景：app、surface、panel、elevated、overlay
文字：primary、secondary、tertiary、invert、disabled
边界：border、border-strong、focus-ring
强调：accent、accent-strong、accent-soft
状态：success、warning、danger、info
组件：control-bg、control-hover、control-active、shadow、radius
```

不需要一开始创建几十个 token；先覆盖窗口、菜单、表单、按钮、状态徽标这几个跨页面高频角色即可。

### 2. 先建立基础组件入口，再迁移页面

建议优先抽出以下最小集合：

- `Modal`：尺寸、标题栏、关闭、遮罩、滚动、Esc、焦点和 `aria` 契约。
- `Popover`/`ContextMenu`：定位、边界修正、层级、Esc、点击外部关闭。
- `Button`：`variant`、`size`、`danger`、`disabled`、focus 状态。
- `FormField`：label、hint、error 与输入控件的统一间距和颜色。
- `Badge`/`Status`：success、warning、danger、running 等状态语义。
- `Toast`：成功、错误、提示的统一生命周期和视觉。

当前 `ContextActionMenu` 可以保留并改为消费 `--lp-*`；`App.tsx` 的 `Modal` 应迁移到 `src/components/ui/Modal.tsx`，新建群、发现版本、路径选择等窗口统一调用它。

新页面的约束应是“组合基础组件 + 页面布局”，而不是“复制一段弹窗 CSS”。这样新增小窗口默认继承主题、间距、圆角、阴影和键盘行为。

### 3. 门禁采用“禁止新增债务”，不要粗暴“一刀切”

颜色扫描器应该分层：

- 允许：`src/shell/tokens.css`、主题定义区、`src/theme.tsx` 的 swatch 数据、明确的图表/头像数据色板。
- 禁止：业务组件 JSX 的 `style={{ color: "#..." }}`、页面 CSS 中新的裸色值、弹窗/菜单/表单的新局部色值。
- 过渡：为 `styles.css` 建立现状 baseline，第一阶段只禁止新增问题，后续每次迁移减少 baseline 数量。

门禁至少包含三项：

1. 每个主题都实现同一组必需语义 token。
2. 业务组件目录不得新增颜色字面量或 `style` 颜色属性。
3. 新增窗口必须使用基础组件；可以用简单的类名/AST 检查，不引入 Storybook、重型 CSS-in-JS 或文档构建工具。

扫描器应报告文件、行号、命中的属性和允许原因；不能只输出“发现 1 个 hex”。

### 4. 用少量真实页面做主题矩阵验收

静态 token 测试不能证明视觉一致。至少覆盖以下状态：

- 新建群/发现版本 Modal
- 成员上下文菜单和二级菜单
- 成员面板中的表单
- Toast、错误态、运行中/排队/失败状态
- 空首页、聊天页、设置页

对七个主题逐一打开这些状态，至少验证背景、文字、边框、按钮、焦点、遮罩和阴影没有回到旧色。已有 Playwright/浏览器验收能力时，优先做一条轻量 smoke；不建议为此引入新的视觉测试平台。

## 推荐实施顺序

### P0：建立规则（半天至一天）

- 盘点 `styles.css`、`themes.css`、`tokens.css` 的职责边界。
- 冻结 `--lp-*` 语义 token 清单和主题必需键集合。
- 把旧变量映射集中到单一 compatibility block。
- 加主题完整性测试和“禁止新增颜色债务”的扫描器。

### P1：收敛高频小窗口（一天至两天）

- 抽取 `Modal`、`Button`、`FormField`、`Popover/ContextMenu`、`Badge`、`Toast`。
- 迁移 `App.tsx` 的 Modal、`ContextActionMenu`、成员添加表单、路径选择和 PmPanel 的优先级颜色。
- 给每个组件补最小行为测试：Esc、点击外部、disabled、danger、主题 token。

### P2：迁移存量页面（两至四天）

- 按“弹窗/表单/状态控件 → 主页面布局 → 装饰细节”迁移 `styles.css`。
- 删除已经被 `themes.css` 覆盖的重复旧规则，避免继续靠加载顺序解决冲突。
- 每批迁移后跑测试和主题矩阵 smoke，不要一次性重写整份 CSS。

### P3：长期约束（持续）

- 把扫描器接入 `test:gate` 和桌面打包前门禁。
- PR 模板要求新页面说明使用了哪些基础组件和 token。
- 每新增一个状态语义，先加 token/组件变体，再写业务页面。

## 不建议的做法

- 不要只做 token 覆盖测试；它不能阻止新组件继续写 `#fff`。
- 不要把所有 hex/rgb 都设为错误；主题源值、swatch、数据可视化和动态头像色会产生误报。
- 不要一次性把 642 行旧 CSS 全部机械替换；容易破坏层叠关系和主题对比度。
- 不要先上重型设计系统工具；当前仓库用 CSS token + React 基础组件 + Vitest/轻量浏览器 smoke 已足够。

## 证据边界

本评估基于本地仓库 `HEAD 7045033` 加当前未提交工作区的静态源码；工作区存在 19 个已修改文件和新增构建脚本，未对其做任何修改。颜色数量没有采用未经说明的扫描结果作为最终指标，后续应以固定脚本输出 baseline 后再比较趋势。

