#!/usr/bin/env node
/*
 * Reproducible PptxGenJS source for 当前wpKnowledge知识飞轮方案.pptx.
 *
 * Example (without changing this repository's package.json or lockfile):
 *   npm install --prefix /tmp/wpknowledge-slides --no-package-lock --no-save pptxgenjs@3.12.0
 *   NODE_PATH=/tmp/wpknowledge-slides/node_modules node knowledge/2.wiki/设计/当前wpKnowledge知识飞轮方案.js
 */

import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "wpKnowledge project team";
pptx.company = "linlisWorkTeam";
pptx.subject = "wpKnowledge PR #20 代码评审与知识飞轮方案汇报";
pptx.title = "当前wpKnowledge知识飞轮方案";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};
pptx.defineSlideMaster({
  title: "BLANK_WIDE",
  background: { color: "F4F7FA" },
  objects: [],
  slideNumber: { x: 12.35, y: 7.10, w: 0.42, h: 0.18, color: "607084", fontFace: "Microsoft YaHei", fontSize: 8, align: "right", margin: 0 },
});

const OUT = path.join(__dirname, "当前wpKnowledge知识飞轮方案.pptx");
const FONT = "Microsoft YaHei";
const MONO = "Aptos Mono";
const C = {
  NAVY: "10253F", NAVY2: "173A5E", INK: "162231", MUTED: "607084",
  BG: "F4F7FA", WHITE: "FFFFFF", CYAN: "16B7C9", CYAN_LIGHT: "DDF6F8",
  BLUE: "3976E8", BLUE_LIGHT: "E8F0FF", GREEN: "229B6A", GREEN_LIGHT: "DFF3E9",
  ORANGE: "E8892E", ORANGE_LIGHT: "FFF0DC", RED: "D95852", RED_LIGHT: "FBE7E5",
  PURPLE: "7656D6", PURPLE_LIGHT: "EDE8FB", LINE: "D7E0E8", LIGHT_TEXT: "C5D3E0",
};

const statusColor = {
  IMPLEMENTED: C.GREEN,
  DEMO: C.ORANGE,
  PLANNED: C.PURPLE,
  "IMPLEMENTED + DEMO": C.BLUE,
  "IMPLEMENTED + PLANNED": C.PURPLE,
};

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: opts.fontFace || FONT,
    fontSize: opts.fontSize || 14,
    color: opts.color || C.INK,
    bold: Boolean(opts.bold),
    italic: Boolean(opts.italic),
    align: opts.align || "left",
    valign: opts.valign || "mid",
    margin: opts.margin === undefined ? 0.04 : opts.margin,
    breakLine: false,
    isTextBox: true,
    ...opts,
  });
}

function addBox(slide, x, y, w, h, opts = {}) {
  const type = opts.radius === false ? pptx.ShapeType.rect : pptx.ShapeType.roundRect;
  slide.addShape(type, {
    x, y, w, h,
    rectRadius: opts.radius === false ? undefined : 0.07,
    fill: { color: opts.fill || C.WHITE, transparency: opts.transparency || 0 },
    line: { color: opts.line || C.LINE, width: opts.lineWidth || 1 },
  });
  if (opts.text) {
    addText(slide, opts.text, x + 0.08, y + 0.04, w - 0.16, h - 0.08, {
      fontSize: opts.fontSize || 13,
      color: opts.color || C.INK,
      bold: opts.bold,
      align: opts.align || "center",
      valign: opts.valign || "mid",
      margin: 0,
    });
  }
}

function addPill(slide, text, x, y, w, fill, opts = {}) {
  addBox(slide, x, y, w, 0.29, {
    text, fill, line: fill, color: opts.color || C.WHITE,
    fontSize: opts.fontSize || 8.6, bold: true,
  });
}

function addLine(slide, x, y, w, h, color = C.LINE, width = 1.4) {
  slide.addShape(pptx.ShapeType.line, { x, y, w, h, line: { color, width } });
}

function addChevron(slide, x, y, color = C.CYAN, w = 0.27, h = 0.38) {
  slide.addShape(pptx.ShapeType.chevron, {
    x, y, w, h,
    fill: { color }, line: { color, transparency: 100 },
  });
}

function addNode(slide, x, y, w, h, title, subtitle, opts = {}) {
  addBox(slide, x, y, w, h, {
    fill: opts.fill || C.WHITE,
    line: opts.accent || C.CYAN,
    lineWidth: 1.3,
  });
  addText(slide, title, x + 0.10, y + 0.07, w - 0.20, 0.29, {
    fontSize: opts.titleSize || 13,
    color: opts.titleColor || C.INK,
    bold: true,
    align: "center",
    margin: 0,
  });
  if (subtitle) {
    addText(slide, subtitle, x + 0.10, y + 0.38, w - 0.20, h - 0.44, {
      fontSize: opts.bodySize || 9.5,
      color: opts.bodyColor || C.MUTED,
      align: "center",
      valign: "top",
      margin: 0,
    });
  }
}

function addRichBox(slide, x, y, w, h, title, items, opts = {}) {
  addBox(slide, x, y, w, h, { fill: opts.fill || C.WHITE, line: opts.line || C.LINE });
  // Intentional overlap: the thin accent bar sits on the card's left border.
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w: 0.07, h,
    fill: { color: opts.accent || C.CYAN }, line: { color: opts.accent || C.CYAN, transparency: 100 },
  });
  addText(slide, title, x + 0.22, y + 0.12, w - 0.34, 0.28, {
    fontSize: opts.titleSize || 15.5,
    color: opts.titleColor || C.INK,
    bold: true,
    margin: 0,
  });
  const itemH = Math.min(0.34, (h - 0.62) / Math.max(items.length, 1));
  items.forEach((item, index) => {
    const iy = y + 0.56 + index * itemH;
    slide.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.24, y: iy + 0.09, w: 0.07, h: 0.07,
      fill: { color: opts.accent || C.CYAN }, line: { color: opts.accent || C.CYAN, transparency: 100 },
    });
    addText(slide, item, x + 0.38, iy, w - 0.54, itemH, {
      fontSize: opts.bodySize || 10.5,
      color: opts.bodyColor || C.MUTED,
      valign: "top",
      margin: 0,
    });
  });
}

function addStatusLegend(slide, dark = false) {
  const y = 6.66;
  addText(slide, "状态口径", 8.18, y, 0.68, 0.21, { fontSize: 8, color: dark ? "B9C9D8" : C.MUTED, bold: true, margin: 0 });
  addPill(slide, "IMPLEMENTED", 8.92, y - 0.02, 1.02, C.GREEN, { fontSize: 7.3 });
  addPill(slide, "DEMO", 10.05, y - 0.02, 0.66, C.ORANGE, { fontSize: 7.3 });
  addPill(slide, "PLANNED", 10.82, y - 0.02, 0.86, C.PURPLE, { fontSize: 7.3 });
  addText(slide, "以实际代码为准", 11.80, y, 0.92, 0.21, { fontSize: 7.6, color: dark ? "B9C9D8" : C.MUTED, align: "right", margin: 0 });
}

function addFrame(title, status, source, opts = {}) {
  const slide = pptx.addSlide("BLANK_WIDE");
  slide.background = { color: opts.dark ? C.NAVY : C.BG };
  const titleColor = opts.dark ? C.WHITE : C.NAVY;
  const muted = opts.dark ? "B9C9D8" : C.MUTED;
  if (opts.kicker) addText(slide, opts.kicker.toUpperCase(), 0.55, 0.29, 4.5, 0.20, { fontSize: 8.5, color: C.CYAN, bold: true, margin: 0 });
  addText(slide, title, 0.55, 0.51, 10.65, 0.48, { fontSize: 22.5, color: titleColor, bold: true, margin: 0 });
  addPill(slide, status, 11.38, 0.44, 1.38, statusColor[status] || C.MUTED, { fontSize: 7.7 });
  addLine(slide, 0.55, 1.17, 12.23, 0, opts.dark ? "31516E" : C.LINE, 1);
  addText(slide, source, 0.55, 7.11, 11.62, 0.17, { fontSize: 7.1, color: muted, valign: "bottom", margin: 0 });
  return slide;
}

function addGridRow(slide, y, cells, xs, widths, opts = {}) {
  cells.forEach((value, index) => {
    addBox(slide, xs[index], y, widths[index], opts.h || 0.52, {
      radius: false,
      fill: opts.fill || C.WHITE,
      line: opts.line || C.LINE,
    });
    addText(slide, value, xs[index] + 0.08, y + 0.04, widths[index] - 0.16, (opts.h || 0.52) - 0.08, {
      fontSize: opts.fontSize || 9.8,
      color: index === 0 && opts.firstColor ? opts.firstColor : (opts.color || C.INK),
      bold: index === 0 && Boolean(opts.firstBold),
      align: opts.alignments ? opts.alignments[index] : "left",
      margin: 0,
    });
  });
}

// 1. Title
{
  const slide = pptx.addSlide("BLANK_WIDE");
  slide.background = { color: C.NAVY };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.CYAN }, line: { color: C.CYAN, transparency: 100 } });
  addText(slide, "WPKNOWLEDGE · PR #20", 0.72, 0.78, 4.0, 0.22, { fontSize: 10, color: C.CYAN, bold: true, margin: 0 });
  addText(slide, "当前wpKnowledge知识飞轮方案", 0.72, 1.28, 11.8, 0.67, { fontSize: 30, color: C.WHITE, bold: true, margin: 0 });
  addText(slide, "代码评审结论 · 多 Agent demo 进度 · 语义分块方案 · 下一步", 0.75, 2.36, 9.2, 0.34, { fontSize: 14.5, color: C.LIGHT_TEXT, margin: 0 });
  addBox(slide, 0.75, 3.32, 11.85, 1.62, { fill: C.NAVY2, line: "31516E" });
  const titleCards = [
    ["本次基线", "PR #20\n776dac5 → b6973a8（代码修复）"],
    ["验证结果", "typecheck / specs\n50 / 50 tests"],
    ["汇报日期", "2026-09-02\nAsia / Beijing"],
  ];
  [1.05, 4.62, 8.18].forEach((x, i) => {
    addText(slide, titleCards[i][0], x, 3.65, 2.8, 0.22, { fontSize: 9, color: C.CYAN, bold: true, margin: 0 });
    addText(slide, titleCards[i][1], x, 4.02, 2.8, 0.56, { fontSize: 14, color: C.WHITE, bold: true, valign: "top", margin: 0 });
  });
  addText(slide, "范围：wpKnowledge 当前分支 codex/embedded-domain-knowledge；domain-knowledge 仅作只读对照。", 0.75, 6.67, 9.4, 0.20, { fontSize: 8.3, color: "9FB2C5", margin: 0 });
  addPill(slide, "IMPLEMENTED", 10.34, 6.61, 1.05, C.GREEN, { fontSize: 7.3 });
  addPill(slide, "DEMO", 11.50, 6.61, 0.66, C.ORANGE, { fontSize: 7.3 });
  addPill(slide, "PLANNED", 12.27, 6.61, 0.82, C.PURPLE, { fontSize: 7.3 });
}

// 2. Review conclusion
{
  const slide = addFrame("评审结论：边界方向正确，两处事实源问题已修复", "IMPLEMENTED",
    "代码：packages/application/src/automated-project-workflow.ts；packages/domain/src/index.ts；commit b6973a8", { kicker: "CODE REVIEW" });
  addRichBox(slide, 0.60, 1.47, 3.82, 2.00, "边界合理", [
    "LangGraph 负责节点调度、重试、取消与 checkpoint",
    "wpKnowledge 保留 Run、版本、证据、Gate 与 Publication",
    "Infrastructure → Ports → Application / Domain 的依赖方向未反转",
  ], { accent: C.GREEN });
  addRichBox(slide, 4.75, 1.47, 3.82, 2.00, "修复 01 · Gate 顺序", [
    "原实现先产生 GateDecision，再运行 Review",
    "现在 Review 后绑定 Oracle / Check / Review 产物",
    "Check 或 Review blocking 会触发 ITERATE / STOPPED",
  ], { accent: C.RED });
  addRichBox(slide, 8.90, 1.47, 3.82, 2.00, "修复 02 · 单一事实源", [
    "GraphState 与 FlywheelRun 都从 iteration 0 起步",
    "workflow_router 不再私自改写业务 Gate 决定",
    "只有 Domain Gate 决定 PASS / ITERATE / STOPPED",
  ], { accent: C.RED });
  addBox(slide, 0.60, 3.83, 12.12, 1.80, { fill: C.NAVY, line: C.NAVY });
  addText(slide, "最终权威链", 0.90, 4.08, 2.0, 0.24, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  const steps = [["CANDIDATE", C.BLUE, 1.45], ["EvaluationReport", C.PURPLE, 1.72], ["GateDecision", C.ORANGE, 1.58], ["wp Publication", C.GREEN, 1.65], ["VERIFIED", C.GREEN, 1.30]];
  let x = 0.90;
  steps.forEach((step, i) => {
    addBox(slide, x, 4.50, step[2], 0.55, { text: step[0], fill: C.NAVY2, line: step[1], color: C.WHITE, fontSize: 10.8, bold: true });
    x += step[2] + 0.32;
    if (i < steps.length - 1) addChevron(slide, x - 0.25, 4.59, C.CYAN, 0.22, 0.34);
  });
  addText(slide, "只有最后一步\n可以写入 VERIFIED", 10.05, 4.19, 2.30, 0.73, { fontSize: 13.5, color: C.WHITE, bold: true, align: "center", margin: 0 });
  addStatusLegend(slide);
}

// 3. Architecture boundary
{
  const slide = addFrame("职责边界：执行状态与业务事实并行，但不互相冒充", "IMPLEMENTED",
    "代码：infrastructure/domain-knowledge/src/{graph,state,runtime}.ts；apps/runner/src/composition.ts:72-129", { kicker: "ARCHITECTURE", dark: true });
  addText(slide, "LANGGRAPH · 执行控制", 0.63, 1.42, 2.8, 0.23, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  addBox(slide, 0.60, 1.77, 5.78, 4.00, { fill: C.NAVY2, line: "31516E" });
  [["GraphState", "currentNode · route · iteration", C.BLUE], ["Checkpoint", "thread_id · resume · attempts", C.PURPLE], ["Projection", "RUNNING / COMPLETED / FAILED", C.CYAN], ["AbortSignal", "协作式取消", C.ORANGE]].forEach((item, i) => {
    addNode(slide, 0.92 + (i % 2) * 2.60, 2.17 + Math.floor(i / 2) * 1.40, 2.25, 0.92, item[0], item[1], { fill: C.NAVY, accent: item[2], titleColor: C.WHITE, bodyColor: "B9C9D8" });
  });
  addText(slide, "不持有 KnowledgeVersion / GateDecision / Publication", 0.92, 5.20, 5.05, 0.29, { fontSize: 10.5, color: C.LIGHT_TEXT, bold: true, align: "center", margin: 0 });
  addText(slide, "WPKNOWLEDGE REGISTRY · 业务事实", 6.94, 1.42, 3.5, 0.23, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  addBox(slide, 6.90, 1.77, 5.82, 4.00, { fill: "F7FAFC", line: "31516E" });
  [["FlywheelRun", "状态 + 业务 iteration", C.BLUE], ["CAS / Evidence", "sha256 不可变引用", C.PURPLE], ["GateDecision", "策略 + reasonCodes", C.ORANGE], ["Publication", "原子写入 VERIFIED", C.GREEN]].forEach((item, i) => {
    addNode(slide, 7.22 + (i % 2) * 2.60, 2.17 + Math.floor(i / 2) * 1.40, 2.25, 0.92, item[0], item[1], { accent: item[2] });
  });
  addText(slide, "业务事件与 SQLite 投影由同一 Application Service 写入", 7.24, 5.20, 5.05, 0.29, { fontSize: 10.5, color: C.INK, bold: true, align: "center", margin: 0 });
  addChevron(slide, 6.48, 3.38, C.CYAN, 0.30, 0.48);
  addText(slide, "Ports / contracts", 5.90, 3.90, 1.45, 0.28, { fontSize: 8.5, color: "B9C9D8", bold: true, align: "center", margin: 0 });
  addStatusLegend(slide, true);
}

// 4. Progress matrix
{
  const slide = addFrame("当前进度：编排骨架已落地，真实 Agent 与语义分块仍未接入", "IMPLEMENTED + DEMO",
    "代码：contracts/src/index.ts:200-216；composition.ts:97-114；tests/acceptance/automated-langgraph-flow.test.ts", { kicker: "PROGRESS" });
  const xs = [0.65, 5.02, 6.74, 8.10, 9.60];
  const ws = [4.35, 1.68, 1.32, 1.46, 3.05];
  addGridRow(slide, 1.44, ["能力", "IMPLEMENTED", "DEMO", "PLANNED", "判断"], xs, ws, { h: 0.43, fill: C.NAVY, line: C.NAVY, color: C.WHITE, fontSize: 9, firstBold: true, alignments: ["left", "center", "center", "center", "left"] });
  const rows = [
    ["7 Agent 节点 + LangGraph 路由", "●", "—", "—", "节点、投影、fan-out/join 可运行"],
    ["SQLite graph checkpoint + Registry/CAS", "●", "—", "—", "两类状态分层持久化"],
    ["ohMyWorkPanel 两轮闭环", "—", "●", "—", "静态资产驱动，不是 live Agent"],
    ["TrustedProjectEvaluator", "●", "●", "—", "真实命令执行；不是敌对沙箱"],
    ["promptAddon-only 配置", "●", "—", "—", "字段边界安全；fixture 不消费 prompt"],
    ["真实 Agent / CodeAgent provider", "—", "—", "●", "自动路径尚未接入"],
    ["拓扑 + 语义切块与增量上下文", "—", "—", "●", "当前 worker 只是机械 fixture"],
    ["进程级取消 / RUNNING 恢复", "—", "—", "●", "只证明协作式取消、部分恢复"],
  ];
  rows.forEach((row, i) => {
    const y = 1.93 + i * 0.56;
    const fill = i % 2 === 0 ? C.WHITE : "EDF2F6";
    addGridRow(slide, y, row, xs, ws, { h: 0.50, fill, line: C.LINE, fontSize: 9.2, firstBold: true, alignments: ["left", "center", "center", "center", "left"] });
    if (row[1] === "●") addText(slide, "●", xs[1], y + 0.05, ws[1], 0.38, { fontSize: 12, color: C.GREEN, bold: true, align: "center", margin: 0 });
    if (row[2] === "●") addText(slide, "●", xs[2], y + 0.05, ws[2], 0.38, { fontSize: 12, color: C.ORANGE, bold: true, align: "center", margin: 0 });
    if (row[3] === "●") addText(slide, "●", xs[3], y + 0.05, ws[3], 0.38, { fontSize: 12, color: C.PURPLE, bold: true, align: "center", margin: 0 });
  });
  addStatusLegend(slide);
}

// 5. Expected orchestration
{
  const slide = addFrame("预期编排：七个 Agent 节点全部保留，评测与发布 Gate 不是 Agent", "IMPLEMENTED + PLANNED",
    "代码：infrastructure/domain-knowledge/src/graph.ts:13-27,106-188；对照 domain-knowledge/docs/report/01-Agent输入输出总览.md", { kicker: "ORCHESTRATION", dark: true });
  const darkNode = { fill: C.NAVY2, titleColor: C.WHITE, bodyColor: "B9C9D8" };
  addNode(slide, 0.55, 2.88, 1.40, 0.80, "Orchestrator", "拆任务 / 组装上下文", { ...darkNode, accent: C.CYAN });
  addChevron(slide, 2.03, 3.07, C.CYAN, 0.24, 0.36);
  addNode(slide, 2.35, 1.63, 1.40, 0.80, "DocWorker × N", "分块证据片段", { ...darkNode, accent: C.BLUE });
  addNode(slide, 2.35, 4.17, 1.40, 0.80, "TestGen", "oracle / 测试意图", { ...darkNode, accent: C.PURPLE });
  addNode(slide, 4.20, 1.63, 1.35, 0.80, "DocGen", "候选知识", { ...darkNode, accent: C.BLUE });
  addNode(slide, 4.20, 4.17, 1.35, 0.80, "Oracle 校验", "非 Agent", { fill: C.NAVY, accent: C.ORANGE, titleColor: C.WHITE, bodyColor: "B9C9D8" });
  addNode(slide, 6.05, 1.63, 1.25, 0.80, "Code", "fresh 实现", { ...darkNode, accent: C.GREEN });
  addNode(slide, 7.78, 1.63, 1.25, 0.80, "Check", "只读检查", { ...darkNode, accent: C.ORANGE });
  addNode(slide, 7.04, 3.51, 1.65, 0.80, "EvalRunner", "独立确定性评测\n非 Agent", { fill: C.NAVY, accent: C.RED, titleColor: C.WHITE, bodyColor: "B9C9D8" });
  addNode(slide, 9.48, 3.51, 1.35, 0.80, "Review", "归因 / Correction", { ...darkNode, accent: C.PURPLE });
  addNode(slide, 11.28, 3.51, 1.42, 0.80, "Publication Gate", "确定性策略\n非 Agent", { fill: C.NAVY, accent: C.GREEN, titleColor: C.WHITE, bodyColor: "B9C9D8" });
  [[3.82, 1.84, C.BLUE], [5.66, 1.84, C.GREEN], [7.41, 1.84, C.ORANGE], [3.82, 4.38, C.PURPLE], [8.88, 3.72, C.PURPLE], [10.94, 3.72, C.GREEN]].forEach(v => addChevron(slide, v[0], v[1], v[2], 0.23, 0.34));
  addLine(slide, 8.38, 2.48, -0.36, 0.96, C.ORANGE, 1.8);
  addLine(slide, 4.88, 5.02, 2.59, -0.63, C.PURPLE, 1.8);
  addLine(slide, 12.02, 4.36, 0, 1.25, C.ORANGE, 1.8);
  addLine(slide, 12.02, 5.61, -10.77, 0, C.ORANGE, 1.8);
  addLine(slide, 1.25, 5.61, 0, -1.84, C.ORANGE, 1.8);
  addText(slide, "ITERATE / ROLLBACK：回到新一轮 Orchestrator", 4.25, 5.73, 4.3, 0.24, { fontSize: 9.3, color: C.ORANGE, bold: true, align: "center", margin: 0 });
  addStatusLegend(slide, true);
}

// 6. Agent I/O overview
{
  const slide = addFrame("七个 Agent 输入输出：职责没有简化，交接只通过受约束产物", "IMPLEMENTED + PLANNED",
    "对照：contracts/src/index.ts:200-216；infrastructure/domain-knowledge/src/agent-definitions.ts；domain-knowledge 报告 Agent 总表", { kicker: "AGENT CONTRACTS" });
  const xs = [0.58, 2.00, 6.05, 10.30], ws = [1.42, 4.05, 4.25, 2.43];
  addGridRow(slide, 1.43, ["Agent", "主要输入", "主要输出", "边界"], xs, ws, { h: 0.44, fill: C.NAVY, line: C.NAVY, color: C.WHITE, fontSize: 9.3, firstBold: true, alignments: ["center", "left", "left", "left"] });
  const rows = [
    ["Orchestrator", "RunPolicy、snapshot、历史 Correction", "任务 DAG、worker 划分、上下文计划", "不生成最终知识"],
    ["DocWorker", "语义块、依赖摘要、公开接口", "证据片段、provenance、未决问题", "不跨块猜测"],
    ["DocGen", "全部 worker 片段、写作规范、历史版本", "候选知识 + 事实引用", "不发布"],
    ["TestGen", "知识契约、公开接口、风险项", "oracle 意图、候选命令/用例", "不读候选实现"],
    ["Code", "候选知识、接口约束、allowed paths", "fresh generated files", "不读参考实现"],
    ["Check", "实现 diff、规则、静态证据", "blocking + findings + 位置", "只读、不定发布"],
    ["Review", "Eval、Check、候选知识、历史", "归因、Correction、unresolved risks", "只读、不选状态"],
  ];
  rows.forEach((row, i) => addGridRow(slide, 1.92 + i * 0.64, row, xs, ws, { h: 0.58, fill: i % 2 === 0 ? C.WHITE : "EDF2F6", line: C.LINE, fontSize: 9.1, firstColor: C.NAVY, firstBold: true, alignments: ["center", "left", "left", "left"] }));
  addStatusLegend(slide);
}

// 7. Current documentation stage
{
  const slide = addFrame("文档生成阶段：并行结构已跑通，但当前内容仍是 deterministic fixture", "DEMO",
    "代码：graph.ts:137-153；automated-project-workflow.ts:143-182；tests/integration/langgraph-infrastructure.test.ts", { kicker: "DOCUMENTATION · CURRENT" });
  addPill(slide, "当前可运行", 0.62, 1.45, 1.12, C.ORANGE, { fontSize: 8 });
  addNode(slide, 0.62, 2.23, 1.45, 0.84, "Orchestrator", "workerCount", { accent: C.CYAN });
  addChevron(slide, 2.17, 2.44, C.CYAN);
  [0, 1, 2].forEach(i => addNode(slide, 2.58, 1.52 + i * 1.12, 1.62, 0.74, `DocWorker ${i + 1}`, "workerId + 固定 fragment", { fill: C.BLUE_LIGHT, accent: C.BLUE, titleSize: 11.5, bodySize: 8.4 }));
  addLine(slide, 4.30, 1.89, 0.90, 0.71, C.BLUE, 1.4);
  addLine(slide, 4.30, 3.01, 0.90, -0.41, C.BLUE, 1.4);
  addLine(slide, 4.30, 4.13, 0.90, -1.53, C.BLUE, 1.4);
  addNode(slide, 5.24, 2.17, 1.72, 0.88, "DocGen", "读取预置 knowledge-v1/v2", { fill: C.BLUE_LIGHT, accent: C.BLUE, bodySize: 8.7 });
  addChevron(slide, 7.06, 2.42, C.CYAN);
  addNode(slide, 7.45, 2.17, 1.72, 0.88, "Candidate", "CAS + provenance", { fill: C.GREEN_LIGHT, accent: C.GREEN });
  addRichBox(slide, 9.55, 1.45, 3.15, 2.03, "这个 demo 能证明", ["Send fan-out / join 路径可执行", "多个 worker ArtifactRef 到达 DocGen context", "节点投影、checkpoint、候选写入可观察"], { accent: C.GREEN, bodySize: 9.5 });
  addRichBox(slide, 9.55, 3.72, 3.15, 2.03, "它不能证明", ["没有函数 / 类 / SCC 级语义切块", "DocGen 没按片段内容聚合写作", "没有增量上下文、冲突消解和覆盖率验证"], { accent: C.RED, bodySize: 9.5 });
  addBox(slide, 0.62, 5.20, 8.55, 0.55, { text: "结论：当前是“拓扑形状正确”的 fixture，不是“拓扑与语义切块已经实现”。", fill: C.ORANGE_LIGHT, line: C.ORANGE, color: C.INK, fontSize: 11.5, bold: true });
  addStatusLegend(slide);
}

// 8. Target semantic/topological chunking
{
  const slide = addFrame("语义 / 拓扑切块：以可解释代码单元为边界，不按 token 生硬截断", "PLANNED",
    "研究：DocAgent, arXiv:2504.08725 (2025-04-11)；domain-knowledge/docs/report/01-Agent输入输出总览.md 文档阶段", { kicker: "DOCUMENTATION · TARGET", dark: true });
  addText(slide, "1 · 建图与稳定边界", 0.65, 1.42, 4.0, 0.24, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  [[0.72, 2.04, "public API", C.BLUE], [2.45, 1.67, "service", C.PURPLE], [2.45, 2.71, "repository", C.GREEN], [4.18, 2.19, "adapter", C.ORANGE]].forEach(v => addNode(slide, v[0], v[1], 1.20, 0.60, v[2], "", { fill: C.NAVY2, accent: v[3], titleColor: C.WHITE, titleSize: 10.5 }));
  addLine(slide, 1.92, 2.34, 0.50, -0.32, C.CYAN, 1.4); addLine(slide, 1.92, 2.34, 0.50, 0.68, C.CYAN, 1.4);
  addLine(slide, 3.67, 2.02, 0.48, 0.44, C.CYAN, 1.4); addLine(slide, 3.67, 3.02, 0.48, -0.56, C.CYAN, 1.4);
  addText(slide, "AST / symbol / import-call graph → SCC 收缩 → 拓扑层\n函数、类、模块、测试簇是候选块；超预算时只在内部语义边界再切。", 0.72, 3.59, 4.72, 0.70, { fontSize: 10.2, color: C.LIGHT_TEXT, valign: "top", margin: 0 });
  addText(slide, "2 · DocWorker 产出证据包", 5.80, 1.42, 3.6, 0.24, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  addRichBox(slide, 5.78, 1.82, 3.02, 2.58, "ChunkEvidence", ["chunkId / symbols / source ranges", "imports / callers / callees / tests", "事实、约束、示例、provenance", "依赖摘要与 unresolved issues"], { fill: C.NAVY2, accent: C.BLUE, titleColor: C.WHITE, bodyColor: C.LIGHT_TEXT, bodySize: 9.2 });
  addText(slide, "3 · DocGen 增量聚合", 9.18, 1.42, 3.4, 0.24, { fontSize: 10.5, color: C.CYAN, bold: true, margin: 0 });
  [["按拓扑序消费", "先依赖，后调用方", C.BLUE], ["增量上下文", "摘要可复用，正文不重复", C.PURPLE], ["验证—重写闭环", "覆盖 / 引用 / 冲突检查", C.GREEN]].forEach((v, i) => addNode(slide, 9.18, 1.82 + i * 0.91, 3.42, 0.67, v[0], v[1], { fill: C.NAVY2, accent: v[2], titleColor: C.WHITE, bodyColor: C.LIGHT_TEXT, titleSize: 11.5, bodySize: 8.8 }));
  addBox(slide, 0.67, 4.77, 11.93, 1.00, { fill: C.NAVY2, line: "31516E" });
  addText(slide, "避免语义截断的判据", 0.93, 4.95, 2.18, 0.23, { fontSize: 9.7, color: C.CYAN, bold: true, margin: 0 });
  addText(slide, "块内可独立解释；跨块依赖显式引用；声明与测试共同归组；循环依赖作为 SCC 整体；\n超 token 时保留接口 + 摘要 + provenance，正文递延，禁止从任意字符位置截断。", 3.00, 4.91, 9.22, 0.55, { fontSize: 10.8, color: C.WHITE, bold: true, valign: "top", margin: 0 });
  addText(slide, "DocAgent 验证了 topological code processing + incremental context building；本项目借用原则，Schema 与 Gate 仍需在 wpKnowledge 内实现。", 0.68, 6.16, 11.9, 0.24, { fontSize: 9.1, color: "B9C9D8", italic: true, margin: 0 });
  addStatusLegend(slide, true);
}

// 9. Code generation and evaluation
{
  const slide = addFrame("代码生成与独立评测：路径隔离已存在，live CodeAgent 尚未接线", "IMPLEMENTED + DEMO",
    "代码：automated-project-workflow.ts:229-309；contracts/src/index.ts:127-197；composition.ts:100-109", { kicker: "CODE + EVALUATION" });
  addText(slide, "候选路径 · 生成后再检查", 0.63, 1.43, 3.3, 0.23, { fontSize: 10, color: C.BLUE, bold: true, margin: 0 });
  addNode(slide, 0.63, 2.04, 1.40, 0.78, "DocGen", "候选知识", { fill: C.BLUE_LIGHT, accent: C.BLUE });
  addChevron(slide, 2.13, 2.25, C.BLUE); addNode(slide, 2.55, 2.04, 1.40, 0.78, "Code", "静态 code-v1/v2", { fill: C.GREEN_LIGHT, accent: C.GREEN });
  addChevron(slide, 4.05, 2.25, C.GREEN); addNode(slide, 4.46, 2.04, 1.40, 0.78, "Check", "blocking / findings", { fill: C.ORANGE_LIGHT, accent: C.ORANGE });
  addText(slide, "Oracle 路径 · 与候选实现隔离", 0.63, 3.48, 3.3, 0.23, { fontSize: 10, color: C.PURPLE, bold: true, margin: 0 });
  addNode(slide, 0.63, 4.09, 1.40, 0.78, "TestGen", "固定命令 fixture", { fill: C.PURPLE_LIGHT, accent: C.PURPLE });
  addChevron(slide, 2.13, 4.30, C.PURPLE); addNode(slide, 2.55, 4.09, 1.82, 0.78, "Reference Oracle", "先验证测试基线", { fill: C.PURPLE_LIGHT, accent: C.PURPLE });
  addLine(slide, 5.88, 2.43, 0.74, 0.78, C.ORANGE, 1.8); addLine(slide, 4.40, 4.47, 2.22, -1.26, C.PURPLE, 1.8);
  addNode(slide, 6.68, 2.72, 2.10, 1.02, "TrustedProjectEvaluator", "归档 workspace 内执行命令\n采集 stdout / stderr / tests", { fill: C.NAVY, accent: C.RED, titleColor: C.WHITE, bodyColor: "D2DDE7", titleSize: 11.2, bodySize: 8.4 });
  addChevron(slide, 8.91, 3.05, C.RED); addNode(slide, 9.38, 2.72, 1.63, 1.02, "Evaluation", "不可变 evidenceRef", { fill: C.RED_LIGHT, accent: C.RED });
  addChevron(slide, 11.12, 3.05, C.RED); addNode(slide, 11.56, 2.72, 1.15, 1.02, "Review", "归因", { fill: C.PURPLE_LIGHT, accent: C.PURPLE });
  addRichBox(slide, 6.68, 4.29, 2.90, 1.49, "已实现", ["allowed path 校验", "reference oracle 先行", "真实 Node 命令 + CAS 证据"], { accent: C.GREEN, bodySize: 9.2 });
  addRichBox(slide, 9.81, 4.29, 2.90, 1.49, "当前边界", ["Code / TestGen 仍读 fixture", "不是 CodeAgent provider", "受信执行器不是敌对沙箱"], { accent: C.ORANGE, bodySize: 9.2 });
  addStatusLegend(slide);
}

// 10. Review and gate
{
  const slide = addFrame("Review / Correction / 迭代：Review 给证据，Gate 才给状态", "IMPLEMENTED",
    "代码：automated-project-workflow.ts:312-374；application/src/index.ts:128-194；domain/src/index.ts:159-196；commit b6973a8", { kicker: "REVIEW LOOP", dark: true });
  const dn = { fill: C.NAVY2, titleColor: C.WHITE, bodyColor: C.LIGHT_TEXT };
  addNode(slide, 0.63, 2.25, 1.58, 0.92, "Evaluation", "tests / stability\ninfrastructureFailure", { ...dn, accent: C.RED });
  addChevron(slide, 2.32, 2.52, C.RED); addNode(slide, 2.72, 2.25, 1.58, 0.92, "Review", "blocking / recommendation\nCorrection", { ...dn, accent: C.PURPLE, bodySize: 8.5 });
  addChevron(slide, 4.42, 2.52, C.PURPLE); addNode(slide, 4.82, 2.06, 2.04, 1.30, "wp Domain Gate", "绑定 body / code / oracle / check / review\n策略产生唯一 GateDecision", { fill: "224867", accent: C.GREEN, titleColor: C.WHITE, bodyColor: "D4E0EA", bodySize: 8.6 });
  [["PASS", "Publication → VERIFIED", C.GREEN], ["ITERATE", "FlywheelRun +1 → 新候选", C.ORANGE], ["STOPPED", "LOW_CONFIDENCE", C.RED]].forEach((v, i) => {
    const y = 1.46 + i * 1.16; addChevron(slide, 7.06, y + 0.22, v[2]); addNode(slide, 7.43, y, 2.02, 0.78, v[0], v[1], { ...dn, accent: v[2] });
  });
  addRichBox(slide, 9.92, 1.46, 2.75, 2.90, "修复后的约束", ["Review 产物先存在，才记录正常 GateDecision", "Check / Review blocking 进入 reasonCodes", "Graph 只执行 GateDecision，不另算 maxIterations", "基础设施失败可跳过 Review，但仍由 Domain Gate STOPPED"], { fill: C.NAVY2, accent: C.CYAN, titleColor: C.WHITE, bodyColor: C.LIGHT_TEXT, bodySize: 8.8 });
  addBox(slide, 0.65, 4.74, 8.78, 0.86, { fill: C.NAVY2, line: "31516E" });
  addText(slide, "Correction 只描述“知识路径 → 失败证据 → 可判定修订标准”；\n它不能直接改状态，也不能绕过 fresh Code / Eval / Gate。", 0.91, 4.93, 8.25, 0.43, { fontSize: 11.2, color: C.WHITE, bold: true, align: "center", margin: 0 });
  addStatusLegend(slide, true);
}

// 11. End-to-end dual lane
{
  const slide = addFrame("端到端流程：LangGraph 推进执行，wpKnowledge 记录可发布事实", "IMPLEMENTED + DEMO",
    "代码：graph.ts；runtime.ts；automated-project-workflow.ts；application/src/index.ts；SQLiteFlywheelRepository", { kicker: "END TO END" });
  addText(slide, "LANGGRAPH", 0.60, 1.42, 1.70, 0.25, { fontSize: 10.5, color: C.BLUE, bold: true, margin: 0 });
  addText(slide, "WPKNOWLEDGE", 0.60, 4.13, 1.70, 0.25, { fontSize: 10.5, color: C.GREEN, bold: true, margin: 0 });
  addLine(slide, 0.58, 3.76, 12.14, 0, C.LINE, 1.1);
  const xs = [0.62, 2.25, 4.02, 5.79, 7.33, 8.86, 10.55], ws = [1.28, 1.42, 1.42, 1.20, 1.20, 1.20, 1.52];
  const top = [["Orchestrate", C.CYAN], ["DocWorker\n+ DocGen", C.BLUE], ["Code + Check", C.GREEN], ["Eval", C.RED], ["Review", C.PURPLE], ["Router", C.ORANGE], ["Publication", C.GREEN]];
  const bottom = [["CREATED\n→ GENERATING", C.BLUE], ["CANDIDATE\n+ CAS refs", C.BLUE], ["GenerationKey\nCOMMITTED", C.PURPLE], ["EvaluationReport\n+ evidence", C.RED], ["GateDecision", C.ORANGE], ["PUBLISHING", C.GREEN], ["VERIFIED", C.GREEN]];
  top.forEach((v, i) => { addBox(slide, xs[i], 2.09, ws[i], 0.72, { text: v[0], fill: C.WHITE, line: v[1], fontSize: 9.8, bold: true }); if (i < top.length - 1) addChevron(slide, xs[i] + ws[i] + 0.08, 2.29, v[1], 0.20, 0.32); });
  bottom.forEach((v, i) => { addBox(slide, xs[i], 4.70, ws[i], 0.72, { text: v[0], fill: C.WHITE, line: v[1], fontSize: 8.9, bold: true }); if (i < bottom.length - 1) addChevron(slide, xs[i] + ws[i] + 0.08, 4.90, v[1], 0.20, 0.32); });
  [1.26, 2.96, 4.73, 6.39, 7.93, 9.46, 11.31].forEach(x => addLine(slide, x, 2.86, 0, 1.79, "A9BAC8", 1));
  addBox(slide, 9.87, 5.82, 2.85, 0.52, { text: "唯一可产生 VERIFIED 的入口", fill: C.GREEN, line: C.GREEN, color: C.WHITE, fontSize: 10.5, bold: true });
  addLine(slide, 11.31, 5.43, 0, 0.38, C.GREEN, 2);
  addText(slide, "ITERATE：GateDecision → FlywheelRun.ITERATING → Graph iteration + 1 → 新一轮；\nGraph checkpoint 不能替代业务事件，业务事件也不能恢复节点局部执行。", 0.65, 5.83, 8.55, 0.47, { fontSize: 9.7, color: C.MUTED, bold: true, valign: "top", margin: 0 });
  addStatusLegend(slide);
}

// 12. Demo evidence and limits
{
  const slide = addFrame("ohMyWorkPanel deterministic fixture：可证明路径，不可证明智能能力", "DEMO",
    "代码：acceptance/ohmyworkpanel/*；tests/acceptance/automated-langgraph-flow.test.ts；automated-project-workflow.ts:137-182", { kicker: "DEMO EVIDENCE" });
  addBox(slide, 0.64, 1.47, 5.78, 0.46, { text: "可以据此下结论", fill: C.GREEN, line: C.GREEN, color: C.WHITE, fontSize: 11.5, bold: true });
  addBox(slide, 6.88, 1.47, 5.78, 0.46, { text: "不能据此下结论", fill: C.RED, line: C.RED, color: C.WHITE, fontSize: 11.5, bold: true });
  const yes = ["七个 Agent 节点均经过 LangGraph", "DocWorker fan-out 后，多个引用到达 DocGen context", "第一轮失败 → ITERATE → 第二轮 PASS", "Oracle / Check / Review 引用进入最终 EvaluationReport", "只有 wpKnowledge Publication 将版本置为 VERIFIED"];
  const no = ["Agent 会基于代码自主生成高质量内容", "DocWorker 已按 AST / 拓扑 / 语义完成分块", "promptAddon 已影响当前 fixture 的实际输出", "worker 真并行吞吐、乱序聚合与部分失败恢复已可靠", "TrustedProjectEvaluator 等同于不可信代码沙箱"];
  yes.forEach((v, i) => { addBox(slide, 0.64, 2.11 + i * 0.76, 5.78, 0.60, { fill: C.GREEN_LIGHT, line: "B8DEC9" }); addText(slide, "✓", 0.83, 2.23 + i * 0.76, 0.25, 0.25, { fontSize: 12, color: C.GREEN, bold: true, align: "center", margin: 0 }); addText(slide, v, 1.16, 2.18 + i * 0.76, 5.03, 0.36, { fontSize: 10, color: C.INK, bold: i === 2 || i === 4, margin: 0 }); });
  no.forEach((v, i) => { addBox(slide, 6.88, 2.11 + i * 0.76, 5.78, 0.60, { fill: C.RED_LIGHT, line: "EAC1BE" }); addText(slide, "×", 7.07, 2.23 + i * 0.76, 0.25, 0.25, { fontSize: 12, color: C.RED, bold: true, align: "center", margin: 0 }); addText(slide, v, 7.40, 2.18 + i * 0.76, 5.03, 0.36, { fontSize: 10, color: C.INK, bold: i === 1 || i === 4, margin: 0 }); });
  addStatusLegend(slide);
}

// 13. Runtime notes
{
  const slide = addFrame("本地运行记录：成功项与环境问题分开描述", "IMPLEMENTED + DEMO",
    "核对：package.json / .github/workflows/ci.yml / package-lock.json；domain-knowledge/src/graph/build-graph.ts；本机实测", { kicker: "RUNTIME NOTES", dark: true });
  const xs = [0.62, 3.07, 8.29], ws = [2.45, 5.22, 4.40];
  addGridRow(slide, 1.45, ["事项", "实际观察", "处理 / 当前口径"], xs, ws, { h: 0.43, fill: "224867", line: "31516E", color: C.WHITE, fontSize: 9.4, firstBold: true });
  const rows = [
    ["Node 版本", "本机 Node 22.22；仓库 engines 与 CI 为 Node 24", "本地可跑；正式结果以 Node 24 CI 为准"],
    ["node:sqlite", "Node 22 测试输出 experimental warning", "属于运行时提示，不是测试失败"],
    ["lockfile registry", "首次写入腾讯镜像，GitHub CI npm ci 出现 ENOTFOUND", "776dac5 已改为 registry.npmjs.org"],
    ["CodeAgent timeout", "domain-knowledge doc-gen 实测约 2–3 分钟，原节点 120s", "上调到 600s；wpKnowledge graph 同为 600s"],
    ["真实 Agent 接入", "wp 自动路径实例化 OhMyWorkPanel fixture executor", "AgentProvider / CodeAgent provider 尚未接入"],
    ["本次验证", "typecheck、validate:specs、npm test", "全部通过；50 / 50 tests"],
  ];
  rows.forEach((row, i) => addGridRow(slide, 1.94 + i * 0.70, row, xs, ws, { h: 0.63, fill: i % 2 === 0 ? C.NAVY2 : "1B4265", line: "31516E", color: "D6E1EA", firstColor: C.WHITE, firstBold: true, fontSize: 9.2 }));
  addStatusLegend(slide, true);
}

// 14. Next steps
{
  const slide = addFrame("下一步：先把语义证据链做实，再扩大 Agent 与运行时能力", "PLANNED",
    "评审结论：PR #20 代码修复 @ b6973a8；domain-knowledge 对照；DocAgent arXiv:2504.08725", { kicker: "NEXT STEPS" });
  const rows = [
    ["P0", "语义 / 拓扑分块", "构建 symbol + import/call/test 图；SCC 与拓扑层；定义 ChunkEvidence Schema；DocGen 真正消费所有 worker 产物。", C.RED],
    ["P0", "接入真实 Agent provider", "让 promptAddon 进入真实请求；固定 base prompt / tools / schema；输出做运行时校验，禁止 Agent 直接决定发布。", C.RED],
    ["P1", "并行、恢复、取消", "补真实 overlap、乱序聚合、worker 部分失败；清理 RUNNING GenerationKey；对子进程做超时与强制终止。", C.ORANGE],
    ["P1", "评测隔离", "从 TrustedProjectEvaluator 演进到不可信代码沙箱；收紧网络、文件、CPU / 内存 / 输出预算。", C.ORANGE],
    ["P2", "增量与质量闭环", "按变更影响子图复用上下文；增加覆盖、引用、冲突、一致性 Gate；用真实仓库样本建立回归集。", C.PURPLE],
  ];
  rows.forEach((row, i) => {
    const y = 1.45 + i * 0.95;
    addPill(slide, row[0], 0.63, y + 0.14, 0.58, row[3], { fontSize: 8 });
    addBox(slide, 1.35, y, 11.35, 0.78, { fill: C.WHITE, line: C.LINE });
    // Intentional overlap: the accent bar is the card's leading rule.
    slide.addShape(pptx.ShapeType.rect, { x: 1.35, y, w: 0.07, h: 0.78, fill: { color: row[3] }, line: { color: row[3], transparency: 100 } });
    addText(slide, row[1], 1.63, y + 0.10, 2.45, 0.26, { fontSize: 11.8, color: C.NAVY, bold: true, margin: 0 });
    addText(slide, row[2], 4.12, y + 0.09, 8.28, 0.50, { fontSize: 9.8, color: C.MUTED, valign: "top", margin: 0 });
  });
  addBox(slide, 0.63, 6.27, 12.07, 0.44, { text: "验收原则：每项能力必须用真实输入、不可变证据和失败用例证明；计划项不得借 fixture 提前标记为 implemented。", fill: C.NAVY, line: C.NAVY, color: C.WHITE, fontSize: 10.3, bold: true });
  addStatusLegend(slide);
}

pptx.writeFile({ fileName: OUT });
