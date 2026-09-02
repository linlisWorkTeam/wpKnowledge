#!/usr/bin/env node
/*
 * 可复现的 PptxGenJS 源文件。
 * 生成：NODE_PATH=/tmp/wpknowledge-slides/node_modules node knowledge/2.wiki/设计/当前wpKnowledge知识飞轮方案.js
 */

import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const pptxgen = require('pptxgenjs');
const pptx = new pptxgen();

pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'wpKnowledge project team';
pptx.company = 'linlisWorkTeam';
pptx.subject = 'wpKnowledge 知识飞轮真实 DSH SDK 演示、使用与 Agent 二次开发';
pptx.title = '当前wpKnowledge知识飞轮方案';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Noto Sans CJK SC',
  bodyFontFace: 'Noto Sans CJK SC',
  lang: 'zh-CN',
};

const OUT = path.join(here, '当前wpKnowledge知识飞轮方案.pptx');
const RUN_SHOT = path.resolve(here, '../../3.workpanel/证据/演示素材/01-真实SDK运行-VERIFIED-深色.png');
const AGENT_SHOT = path.resolve(here, '../../3.workpanel/证据/演示素材/02-Agent有限定制-浅色.png');
const FONT = 'Noto Sans CJK SC';
const MONO = 'Noto Sans Mono CJK SC';
const C = {
  NAVY: '0A1828', NAVY2: '112A42', NAVY3: '183B59',
  INK: '132238', MUTED: '60738A', PALE: 'AFC2D3', BG: 'F3F7FA', WHITE: 'FFFFFF',
  CYAN: '24C8D8', CYAN_LIGHT: 'DDF8FA', BLUE: '397CE8', BLUE_LIGHT: 'E7F0FF',
  GREEN: '23A36D', GREEN_LIGHT: 'DFF4E9', ORANGE: 'EA8A2F', ORANGE_LIGHT: 'FFF0DB',
  RED: 'DB5A55', RED_LIGHT: 'FBE7E5', PURPLE: '8064DB', PURPLE_LIGHT: 'EEE9FC',
  LINE: 'D5E0E8', GOLD: 'D9A928', GOLD_LIGHT: 'FFF7D8',
};

pptx.defineSlideMaster({
  title: 'BASE',
  background: { color: C.BG },
  objects: [],
  slideNumber: {
    x: 12.40, y: 7.12, w: 0.35, h: 0.16,
    color: C.MUTED, fontFace: FONT, fontSize: 8, align: 'right', margin: 0,
  },
});

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x, y, w, h,
    fontFace: opts.fontFace || FONT,
    fontSize: opts.fontSize || 13,
    color: opts.color || C.INK,
    bold: Boolean(opts.bold),
    italic: Boolean(opts.italic),
    align: opts.align || 'left',
    valign: opts.valign || 'mid',
    margin: opts.margin === undefined ? 0.03 : opts.margin,
    breakLine: false,
    fit: 'shrink',
    ...opts,
  });
}

function box(slide, x, y, w, h, opts = {}) {
  const shape = opts.square ? pptx.ShapeType.rect : pptx.ShapeType.roundRect;
  slide.addShape(shape, {
    x, y, w, h,
    fill: { color: opts.fill || C.WHITE, transparency: opts.transparency || 0 },
    line: { color: opts.line || C.LINE, width: opts.lineWidth || 1, transparency: opts.lineTransparency || 0 },
    radius: opts.square ? 0 : 0.06,
  });
  if (opts.label) text(slide, opts.label, x + 0.08, y + 0.04, w - 0.16, h - 0.08, {
    fontSize: opts.fontSize || 11, color: opts.color || C.INK, bold: opts.bold,
    align: opts.align || 'center', valign: opts.valign || 'mid', margin: 0,
  });
}

function pill(slide, label, x, y, w, fill, opts = {}) {
  box(slide, x, y, w, 0.30, { label, fill, line: fill, color: opts.color || C.WHITE, fontSize: opts.fontSize || 8, bold: true });
}

function line(slide, x, y, w, h, color = C.LINE, width = 1.4, arrow = false) {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h,
    line: { color, width, ...(arrow ? { endArrowType: 'triangle' } : {}) },
  });
}

function arrow(slide, x, y, w = 0.34, color = C.CYAN) {
  slide.addShape(pptx.ShapeType.chevron, {
    x, y, w, h: 0.34,
    fill: { color }, line: { color, transparency: 100 },
  });
}

function node(slide, x, y, w, h, title, subtitle, opts = {}) {
  box(slide, x, y, w, h, { fill: opts.fill || C.WHITE, line: opts.accent || C.CYAN, lineWidth: 1.3 });
  text(slide, title, x + 0.10, y + 0.07, w - 0.20, 0.27, {
    fontSize: opts.titleSize || 12, color: opts.titleColor || C.INK, bold: true, align: 'center', margin: 0,
  });
  if (subtitle) text(slide, subtitle, x + 0.10, y + 0.36, w - 0.20, h - 0.42, {
    fontSize: opts.bodySize || 9, color: opts.bodyColor || C.MUTED, align: 'center', valign: 'top', margin: 0,
  });
}

function card(slide, x, y, w, h, title, items, opts = {}) {
  box(slide, x, y, w, h, { fill: opts.fill || C.WHITE, line: opts.line || C.LINE });
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w: 0.07, h,
    fill: { color: opts.accent || C.CYAN }, line: { color: opts.accent || C.CYAN, transparency: 100 },
  });
  text(slide, title, x + 0.23, y + 0.13, w - 0.37, 0.28, {
    fontSize: opts.titleSize || 15, color: opts.titleColor || C.INK, bold: true, margin: 0,
  });
  const itemH = Math.min(0.37, (h - 0.66) / Math.max(1, items.length));
  items.forEach((item, index) => {
    const yy = y + 0.56 + index * itemH;
    slide.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.24, y: yy + 0.10, w: 0.07, h: 0.07,
      fill: { color: opts.accent || C.CYAN }, line: { color: opts.accent || C.CYAN, transparency: 100 },
    });
    text(slide, item, x + 0.39, yy, w - 0.56, itemH, {
      fontSize: opts.bodySize || 10, color: opts.bodyColor || C.MUTED, valign: 'top', margin: 0,
    });
  });
}

function frame(title, kicker, status, opts = {}) {
  const slide = pptx.addSlide('BASE');
  const dark = Boolean(opts.dark);
  slide.background = { color: dark ? C.NAVY : C.BG };
  text(slide, kicker.toUpperCase(), 0.56, 0.27, 4.2, 0.20, { fontSize: 8.5, color: C.CYAN, bold: true, margin: 0 });
  text(slide, title, 0.56, 0.50, 10.65, 0.48, { fontSize: 22, color: dark ? C.WHITE : C.NAVY, bold: true, margin: 0 });
  const statusColor = status === '已实现' ? C.GREEN : status === '真实证据' ? C.BLUE : status === '边界' ? C.ORANGE : C.PURPLE;
  pill(slide, status, 11.55, 0.45, 1.15, statusColor, { fontSize: 8.2 });
  line(slide, 0.56, 1.16, 12.14, 0, dark ? '31516E' : C.LINE, 1);
  text(slide, opts.source || 'wpKnowledge · 2026-09-02', 0.56, 7.10, 11.40, 0.17, {
    fontSize: 7.4, color: dark ? C.PALE : C.MUTED, margin: 0,
  });
  return slide;
}

function gridRow(slide, y, cells, xs, ws, opts = {}) {
  cells.forEach((cell, index) => {
    box(slide, xs[index], y, ws[index], opts.h || 0.52, {
      square: true, fill: opts.fill || C.WHITE, line: opts.line || C.LINE,
    });
    text(slide, cell, xs[index] + 0.07, y + 0.04, ws[index] - 0.14, (opts.h || 0.52) - 0.08, {
      fontSize: opts.fontSize || 9.5,
      color: opts.color || C.INK,
      bold: opts.header || (index === 0 && opts.firstBold),
      align: opts.alignments?.[index] || 'left', margin: 0,
    });
  });
}

function addImageContain(slide, imagePath, x, y, w, h, pixelW, pixelH) {
  const scale = Math.min(w / pixelW, h / pixelH);
  const iw = pixelW * scale;
  const ih = pixelH * scale;
  slide.addImage({ path: imagePath, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih });
}

// 1 · 封面
{
  const slide = pptx.addSlide('BASE');
  slide.background = { color: C.NAVY };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.CYAN }, line: { color: C.CYAN, transparency: 100 } });
  text(slide, 'WPKNOWLEDGE · KNOWLEDGE FLYWHEEL', 0.76, 0.75, 5.0, 0.22, { fontSize: 10, color: C.CYAN, bold: true, margin: 0 });
  text(slide, '当前 wpKnowledge\n知识飞轮方案', 0.76, 1.23, 8.5, 1.22, { fontSize: 31, color: C.WHITE, bold: true, valign: 'top', margin: 0 });
  text(slide, '真实 DeepSeek Harness SDK 闭环 · ohMyWorkPanel Demo · 使用与 Agent 二次开发', 0.79, 2.72, 10.8, 0.35, { fontSize: 14, color: C.PALE, margin: 0 });
  box(slide, 0.78, 3.48, 11.82, 1.73, { fill: C.NAVY2, line: '31516E' });
  const facts = [
    ['真实闭环', 'VERIFIED / PASS\n1 次唯一发布'],
    ['模型调用', '8 次\n7 成功 + 1 恢复'],
    ['可审计性', '14 节点 · 46 事件\n12 / 12 工件完整'],
  ];
  [1.08, 4.84, 8.63].forEach((x, i) => {
    text(slide, facts[i][0], x, 3.78, 2.8, 0.23, { fontSize: 9.2, color: C.CYAN, bold: true, margin: 0 });
    text(slide, facts[i][1], x, 4.13, 2.95, 0.68, { fontSize: 15, color: C.WHITE, bold: true, valign: 'top', margin: 0 });
  });
  box(slide, 0.78, 5.72, 8.55, 0.72, { fill: C.NAVY3, line: '31516E' });
  text(slide, '一句话：用真实源码生成可追溯知识，再用这份知识驱动隔离的代码重建与确定性评测。', 1.02, 5.89, 8.05, 0.33, { fontSize: 11.3, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  pill(slide, '2026-09-02', 10.42, 5.93, 1.15, C.BLUE, { fontSize: 8 });
  pill(slide, 'PR #22', 11.72, 5.93, 0.84, C.PURPLE, { fontSize: 8 });
  text(slide, '固定样例：ohMyWorkPanel @ 3b2e6073e01b42e2a595fca4de3acaad44715ddd', 0.78, 6.75, 9.8, 0.18, { fontFace: MONO, fontSize: 8.1, color: '91A9BC', margin: 0 });
}

// 2 · 用户价值
{
  const slide = frame('用户怎样使用：启动一次治理，拿到能追责的知识版本', 'PRODUCT OUTCOME', '已实现', {
    source: '入口：src/interfaces/runner/cli.ts、server.ts；业务事实：SQLite Registry + CAS',
  });
  const steps = [
    ['1', '固定来源', '仓库路径 + commit\n来源不可漂移', C.BLUE],
    ['2', '启动 Run', 'CLI / HTTP / Console\n选择固定 profile', C.CYAN],
    ['3', '观察节点', '并行、失败、恢复\n实时投影到前台', C.PURPLE],
    ['4', '检查证据', '知识、评测、Gate\nSHA-256 可核验', C.ORANGE],
    ['5', '查询与反馈', '仅 PASS 后发布\nDSH 查询 + 反馈', C.GREEN],
  ];
  steps.forEach((s, i) => {
    const x = 0.60 + i * 2.48;
    slide.addShape(pptx.ShapeType.ellipse, { x: x + 0.72, y: 1.55, w: 0.56, h: 0.56, fill: { color: s[3] }, line: { color: s[3] } });
    text(slide, s[0], x + 0.72, 1.60, 0.56, 0.38, { fontSize: 13, color: C.WHITE, bold: true, align: 'center', margin: 0 });
    node(slide, x, 2.27, 2.03, 1.25, s[1], s[2], { accent: s[3], fill: i === 4 ? C.GREEN_LIGHT : C.WHITE, titleSize: 13, bodySize: 9.4 });
    if (i < steps.length - 1) arrow(slide, x + 2.10, 2.72, 0.25, s[3]);
  });
  card(slide, 0.62, 4.13, 5.82, 1.60, '用户得到的不是一段聊天记录', [
    '可版本化的 KnowledgeVersion 与 pinned provenance',
    '可复验的 EvaluationReport、GateDecision 和 Publication receipt',
    '按 runId 导出的脱敏 Demo 报告',
  ], { accent: C.GREEN, bodySize: 10.2 });
  card(slide, 6.82, 4.13, 5.82, 1.60, '两个前台，各管一件事', [
    'wpKnowledge Console：业务状态、证据、发布与 Agent 角色配置',
    'DSH Web：Harness 会话调试；不拥有知识发布权',
    '公网 DSH 仅用于临时联调，当前没有 TLS',
  ], { accent: C.ORANGE, bodySize: 10.2 });
}

// 3 · 架构边界
{
  const slide = frame('目标架构：wpKnowledge 管治理，domain-knowledge 管执行', 'ARCHITECTURE', '已实现', {
    dark: true,
    source: 'ARCHITECTURE.md；src/infrastructure/workflow/langgraph；src/interfaces/runner/composition.ts',
  });
  text(slide, '上层 · 知识治理事实源', 0.62, 1.42, 3.6, 0.23, { fontSize: 10, color: C.CYAN, bold: true, margin: 0 });
  box(slide, 0.62, 1.79, 12.03, 1.48, { fill: C.NAVY2, line: '31516E' });
  [['FlywheelRun', C.BLUE], ['KnowledgeVersion', C.CYAN], ['EvaluationReport', C.RED], ['GateDecision', C.ORANGE], ['Publication', C.GREEN], ['Event / Audit', C.PURPLE]].forEach((v, i) => {
    node(slide, 0.88 + i * 1.92, 2.05, 1.56, 0.78, v[0], i === 4 ? '唯一 VERIFIED 入口' : 'wpKnowledge authority', { fill: C.NAVY, accent: v[1], titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 10.4, bodySize: 7.8 });
  });
  text(slide, '基础设施层 · 工作流执行', 0.62, 3.58, 3.6, 0.23, { fontSize: 10, color: C.CYAN, bold: true, margin: 0 });
  box(slide, 0.62, 3.95, 7.52, 1.67, { fill: C.NAVY2, line: '31516E' });
  [['LangGraph', '拓扑 / 并行 / 循环'], ['GraphState', '节点执行状态'], ['Checkpoint', '恢复 / attempt'], ['Projection', '给前台观察']].forEach((v, i) => node(slide, 0.88 + i * 1.77, 4.28, 1.46, 0.91, v[0], v[1], { fill: C.NAVY, accent: [C.CYAN, C.BLUE, C.PURPLE, C.GREEN][i], titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 10.7, bodySize: 8.2 }));
  box(slide, 8.48, 3.95, 4.17, 1.67, { fill: 'F5F9FC', line: C.CYAN });
  text(slide, 'Agent Provider', 8.77, 4.21, 3.6, 0.28, { fontSize: 14.5, color: C.NAVY, bold: true, align: 'center', margin: 0 });
  text(slide, 'DeepSeekHarnessSdkAgent\n→ OpenCode Go / deepseek-v4-flash', 8.78, 4.62, 3.58, 0.54, { fontSize: 11, color: C.MUTED, bold: true, align: 'center', valign: 'top', margin: 0 });
  box(slide, 0.62, 6.02, 12.03, 0.55, { fill: C.ORANGE, line: C.ORANGE, label: '重要：code 是 LangGraph 的代码生成角色，不是独立安装的 CodeAgent 产品，也不是公司 CodeAgent CLI。', color: C.WHITE, fontSize: 11.2, bold: true });
}

// 4 · 预期编排
{
  const slide = frame('预期 Agent 编排：七类角色可观察，Gate 与评测不是 Agent', 'EXPECTED ORCHESTRATION', '已实现', {
    dark: true,
    source: 'src/infrastructure/workflow/langgraph/graph.ts；agent-definitions.ts',
  });
  const dn = { fill: C.NAVY2, titleColor: C.WHITE, bodyColor: C.PALE };
  node(slide, 0.55, 2.75, 1.40, 0.88, 'Orchestrator', '固定职责\n组装本轮计划', { ...dn, accent: C.CYAN });
  arrow(slide, 2.03, 2.99, 0.25, C.CYAN);
  node(slide, 2.36, 1.51, 1.48, 0.88, 'DocWorker × N', '读取分块来源\n提取证据', { ...dn, accent: C.BLUE, titleSize: 11.2 });
  node(slide, 2.36, 4.25, 1.48, 0.88, 'TestGen', '读取真实源码\n提出测试意图', { ...dn, accent: C.PURPLE });
  arrow(slide, 3.94, 1.77, 0.25, C.BLUE);
  node(slide, 4.28, 1.51, 1.42, 0.88, 'DocGen', '写候选知识\n接收 Correction', { ...dn, accent: C.BLUE });
  node(slide, 4.28, 4.25, 1.42, 0.88, 'Oracle 校验', '确定性组件\n先验真值', { fill: C.NAVY, accent: C.ORANGE, titleColor: C.WHITE, bodyColor: C.PALE });
  arrow(slide, 5.80, 1.77, 0.25, C.GREEN);
  node(slide, 6.13, 1.51, 1.48, 0.88, 'code 角色', '新会话重建实现\n只看知识 + 接口', { ...dn, accent: C.GREEN });
  arrow(slide, 7.70, 1.77, 0.25, C.ORANGE);
  node(slide, 8.04, 1.51, 1.38, 0.88, 'Check', '只读检查\n不能修改代码', { ...dn, accent: C.ORANGE });
  line(slide, 8.74, 2.42, -0.40, 0.97, C.ORANGE, 1.7, true);
  line(slide, 5.00, 5.13, 3.05, -1.38, C.PURPLE, 1.7, true);
  node(slide, 7.28, 3.47, 1.78, 0.96, 'Evaluator', '物化 CAS 代码\n执行确定性命令', { fill: C.NAVY, accent: C.RED, titleColor: C.WHITE, bodyColor: C.PALE });
  arrow(slide, 9.18, 3.76, 0.25, C.RED);
  node(slide, 9.52, 3.47, 1.42, 0.96, 'Review', '依据 Eval + Check\n给归因 / Correction', { ...dn, accent: C.PURPLE });
  arrow(slide, 11.05, 3.76, 0.25, C.PURPLE);
  node(slide, 11.39, 3.47, 1.38, 0.96, 'wp Gate', '规则判定\nPASS / ITERATE', { fill: C.NAVY, accent: C.GREEN, titleColor: C.WHITE, bodyColor: C.PALE });
  line(slide, 12.08, 4.48, 0, 1.13, C.ORANGE, 1.7);
  line(slide, 12.08, 5.61, -10.76, 0, C.ORANGE, 1.7);
  line(slide, 1.32, 5.61, 0, -1.85, C.ORANGE, 1.7, true);
  text(slide, 'ITERATE / ROLLBACK：回到下一轮 Orchestrator；PASS：进入唯一 Publication。', 3.40, 5.76, 6.7, 0.29, { fontSize: 10, color: C.ORANGE, bold: true, align: 'center', margin: 0 });
  box(slide, 0.62, 6.26, 12.03, 0.43, { fill: C.NAVY3, line: '31516E', label: '节点上的职责、拓扑、输入输出 Schema 与工具权限固定；操作者只能追加提示词。', color: C.WHITE, fontSize: 10.2, bold: true });
}

// 5 · 真实端到端
{
  const slide = frame('一次真实 E2E：格式失败没有抹掉，恢复后仍由 Gate 决定发布', 'LIVE END TO END', '真实证据', {
    source: 'run 5503b6bc-0350-4b53-98cc-6fbf3a13aaa9；脱敏报告 04-SDK成功运行-脱敏报告.json',
  });
  const stages = [
    ['来源', 'pinned commit', C.BLUE], ['编排', 'orchestrator', C.CYAN], ['并行', 'worker + test', C.PURPLE],
    ['知识', 'doc-gen retry', C.ORANGE], ['重建', 'code role', C.GREEN], ['验证', 'check + eval', C.RED],
    ['评审', 'review', C.PURPLE], ['发布', 'VERIFIED', C.GREEN],
  ];
  stages.forEach((s, i) => {
    const x = 0.58 + i * 1.53;
    node(slide, x, 1.63, 1.18, 0.86, s[0], s[1], { accent: s[2], fill: i === 7 ? C.GREEN_LIGHT : C.WHITE, titleSize: 11, bodySize: 8.2 });
    if (i < stages.length - 1) arrow(slide, x + 1.23, 1.89, 0.22, s[2]);
  });
  box(slide, 4.94, 2.70, 2.06, 0.48, { fill: C.RED_LIGHT, line: C.RED, label: 'DocGen #1：非 JSON', color: C.RED, fontSize: 9.5, bold: true });
  line(slide, 5.97, 2.50, 0, 0.19, C.RED, 1.5);
  box(slide, 0.62, 3.59, 12.02, 1.48, { fill: C.NAVY, line: C.NAVY });
  const metrics = [
    ['最终状态', 'VERIFIED / PASS'], ['模型调用', '8（7 成功 + 1 失败）'], ['节点 / 事件', '14 / 46'],
    ['知识质量', '96 / 100'], ['行为评测', '1 / 1 · stability 1'], ['证据', '12 / 12 SHA-256'],
  ];
  metrics.forEach((m, i) => {
    const x = 0.93 + (i % 3) * 3.85;
    const y = 3.84 + Math.floor(i / 3) * 0.57;
    text(slide, m[0], x, y, 1.30, 0.22, { fontSize: 8.3, color: C.CYAN, bold: true, margin: 0 });
    text(slide, m[1], x + 1.28, y - 0.02, 2.30, 0.27, { fontSize: 11.2, color: C.WHITE, bold: true, margin: 0 });
  });
  card(slide, 0.62, 5.40, 3.77, 1.06, 'Checkpoint 做了什么', ['同一 runId 恢复，已提交副作用不重复'], { accent: C.PURPLE, bodySize: 10.2, titleSize: 13 });
  card(slide, 4.77, 5.40, 3.77, 1.06, 'Evaluator 做了什么', ['只认实际命令结果，不接受 Agent 自评分'], { accent: C.RED, bodySize: 10.2, titleSize: 13 });
  card(slide, 8.92, 5.40, 3.72, 1.06, 'Gate 做了什么', ['绑定证据后原子发布，产生唯一 receipt'], { accent: C.GREEN, bodySize: 10.2, titleSize: 13 });
}

// 6 · Demo 进度
{
  const slide = frame('多 Agent Demo 进度：三次运行分别验证闭环、拒绝与恢复', 'DEMO PROGRESS', '真实证据', {
    source: 'knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md',
  });
  const runs = [
    ['A · Headless 兼容样例', 'VERIFIED / PASS', '质量 65 → 98；第二轮通过 295 / 295；唯一发布', C.BLUE],
    ['B · SDK 隔离失败样例', 'FAIL CLOSED', '28 次 Agent 调用；45 节点；31 / 31 工件完整；越界测试文件被拒绝；0 发布', C.RED],
    ['C · SDK 完整样例', 'VERIFIED / PASS', 'DocGen 非 JSON 后同 Run 恢复；1 / 1 评测；12 / 12 工件；唯一发布', C.GREEN],
  ];
  runs.forEach((r, i) => {
    const y = 1.49 + i * 1.41;
    box(slide, 0.65, y, 12.00, 1.08, { fill: i === 1 ? C.RED_LIGHT : i === 2 ? C.GREEN_LIGHT : C.BLUE_LIGHT, line: r[3] });
    pill(slide, r[1], 10.74, y + 0.17, 1.52, r[3], { fontSize: 7.8 });
    text(slide, r[0], 0.97, y + 0.17, 4.0, 0.26, { fontSize: 14, color: C.NAVY, bold: true, margin: 0 });
    text(slide, r[2], 0.97, y + 0.55, 10.95, 0.31, { fontSize: 10.3, color: C.MUTED, bold: true, margin: 0 });
  });
  box(slide, 0.65, 5.92, 12.00, 0.57, { fill: C.NAVY, line: C.NAVY, label: '一次成功不是稳定性结论；失败样例也不是废数据，它证明了系统会拒绝越界并保留现场。', color: C.WHITE, fontSize: 11.1, bold: true });
}

// 7 · 控制台截图
{
  const slide = frame('前台已经能看到 LangGraph 节点，也能分辨失败与恢复', 'CONSOLE EVIDENCE', '真实证据', {
    dark: true,
    source: '真实只读 Console 截图；run 5503b6bc-0350-4b53-98cc-6fbf3a13aaa9',
  });
  box(slide, 0.62, 1.40, 5.05, 5.44, { fill: '07121E', line: '31516E' });
  addImageContain(slide, RUN_SHOT, 0.76, 1.54, 4.77, 5.16, 1600, 1906);
  card(slide, 6.02, 1.48, 6.61, 1.33, '前台读的是业务投影', [
    '节点状态由 LangGraph 执行产生，但写进 wpKnowledge Registry 后再展示',
    'Graph checkpoint 不直接暴露给产品 UI',
  ], { fill: C.NAVY2, accent: C.CYAN, titleColor: C.WHITE, bodyColor: C.PALE, bodySize: 9.7 });
  card(slide, 6.02, 3.08, 6.61, 1.33, '失败没有被“洗绿”', [
    'DocGen attempt 1 明确标红；attempt 2 完成后继续',
    '最终 PASS 来自 EvaluationReport + Domain Gate',
  ], { fill: C.NAVY2, accent: C.RED, titleColor: C.WHITE, bodyColor: C.PALE, bodySize: 9.7 });
  card(slide, 6.02, 4.68, 6.61, 1.33, '可导出的审计材料', [
    'Run、节点、事件、checkpoint、评测、发布和 Agent 调用摘要',
    '不包含密钥、Prompt 正文、模型正文或会话日志',
  ], { fill: C.NAVY2, accent: C.GREEN, titleColor: C.WHITE, bodyColor: C.PALE, bodySize: 9.7 });
}

// 8 · Agent I/O
{
  const slide = frame('七类 Agent 角色的输入输出：职责固定，执行后端可统一', 'AGENT INPUT / OUTPUT', '已实现', {
    source: 'src/infrastructure/workflow/langgraph/agent-definitions.ts；src/application/services/automated-project-workflow.ts',
  });
  const xs = [0.58, 2.25, 6.05, 10.15];
  const ws = [1.67, 3.80, 4.10, 2.55];
  gridRow(slide, 1.42, ['角色', '可见输入', '结构化输出', '不能做'], xs, ws, { h: 0.43, fill: C.NAVY, line: C.NAVY, color: C.WHITE, header: true, fontSize: 9.1, alignments: ['center', 'left', 'left', 'left'] });
  const rows = [
    ['Orchestrator', '策略、轮次、执行摘要', '本轮计划摘要', '改拓扑 / 发布'],
    ['DocWorker', '被分配源码、公开接口', '片段 + provenance', '跨块猜测 / Gate'],
    ['DocGen', '来源快照、片段、Correction', '知识正文 + 元数据', '发布 / 自评通过'],
    ['TestGen', '参考源码、公开接口', '候选命令 / oracle 意图', '读取候选知识'],
    ['code 角色', '候选知识、公开接口、允许路径', '生成文件列表', '读参考实现 / 测试'],
    ['Check', '内联生成代码、判据', 'blocking + findings', '改代码 / 发布'],
    ['Review', '知识、Eval、Check', 'PASS 建议或 Correction', '直接改状态'],
  ];
  rows.forEach((r, i) => gridRow(slide, 1.91 + i * 0.65, r, xs, ws, {
    h: 0.58, fill: i % 2 === 0 ? C.WHITE : 'EAF1F6', line: C.LINE, fontSize: 9.1,
    firstBold: true, alignments: ['center', 'left', 'left', 'left'],
  }));
  box(slide, 0.58, 6.60, 12.12, 0.33, { fill: C.ORANGE_LIGHT, line: C.ORANGE, label: '所有角色本次都由 DeepSeekHarnessSdkAgent 执行；“角色不同”不等于“安装了七个不同 Agent 产品”。', color: C.INK, fontSize: 9.5, bold: true });
}

// 9 · 文档阶段与分块
{
  const slide = frame('文档生成如何分块：当前单 worker 已实跑，语义 fan-out 仍要补', 'DOCUMENT GENERATION', '边界', {
    source: 'graph.ts 的 Send fan-out；automated-project-workflow.ts 的 assignedSourcePaths；当前 Demo workers=1',
  });
  text(slide, '当前真实路径', 0.63, 1.41, 2.0, 0.24, { fontSize: 10.3, color: C.BLUE, bold: true, margin: 0 });
  node(slide, 0.63, 1.89, 1.55, 0.87, 'SourceSnapshot', '固定 commit\nmanifest + provenance', { accent: C.BLUE });
  arrow(slide, 2.30, 2.15, 0.25, C.BLUE);
  node(slide, 2.64, 1.89, 1.60, 0.87, 'DocWorker × 1', '按 sourcePaths 索引\n分配来源文件', { accent: C.CYAN });
  arrow(slide, 4.35, 2.15, 0.25, C.CYAN);
  node(slide, 4.69, 1.89, 1.60, 0.87, 'DocGen', '汇总片段\n生成 5,165B 正文', { accent: C.GREEN });
  arrow(slide, 6.41, 2.15, 0.25, C.GREEN);
  node(slide, 6.75, 1.89, 1.60, 0.87, 'Quality Gate', '96 / 100\n结构与可验证性', { accent: C.ORANGE, fill: C.GREEN_LIGHT });
  card(slide, 8.78, 1.46, 3.86, 1.69, '当前能证明', [
    'LangGraph 的 fan-out / join 路径存在',
    'worker 产物以 ArtifactRef 汇入 DocGen',
    '质量不足会跳过代码生成并进入下一轮',
  ], { accent: C.GREEN, bodySize: 9.4 });
  text(slide, '大仓库目标', 0.63, 3.52, 2.0, 0.24, { fontSize: 10.3, color: C.PURPLE, bold: true, margin: 0 });
  const future = [
    ['建图', 'symbol / import / call / test'], ['收缩', 'SCC 保留循环语义'], ['分层', '按拓扑序生成稳定块'],
    ['证据包', '事实 + 引用 + unresolved'], ['增量聚合', '只重做受影响子图'],
  ];
  future.forEach((f, i) => {
    const x = 0.63 + i * 2.43;
    node(slide, x, 4.04, 1.98, 0.92, f[0], f[1], { accent: C.PURPLE, fill: C.PURPLE_LIGHT, titleSize: 11.5, bodySize: 8.7 });
    if (i < future.length - 1) arrow(slide, x + 2.05, 4.33, 0.24, C.PURPLE);
  });
  box(slide, 0.63, 5.39, 12.01, 0.94, { fill: C.NAVY, line: C.NAVY });
  text(slide, '禁止按字符或 token 任意截断。块必须能独立解释，跨块依赖必须显式引用；超预算时保留接口、摘要和 provenance，正文延迟生成。', 0.93, 5.65, 11.42, 0.40, { fontSize: 11.1, color: C.WHITE, bold: true, align: 'center', margin: 0 });
}

// 10 · 代码生成与评测
{
  const slide = frame('代码生成与评测：两条隔离链路只在确定性 Evaluator 汇合', 'CODE + EVALUATION', '已实现', {
    dark: true,
    source: 'AgentWorkspaceProvider；isolation-launcher.mjs；TrustedProjectEvaluator；allowedGeneratedPaths 动态 Schema',
  });
  text(slide, '候选链 · 不读参考实现', 0.62, 1.40, 3.1, 0.24, { fontSize: 10.2, color: C.GREEN, bold: true, margin: 0 });
  node(slide, 0.63, 1.90, 1.62, 0.84, '候选知识', 'CAS bodyRef', { fill: C.NAVY2, accent: C.BLUE, titleColor: C.WHITE, bodyColor: C.PALE });
  arrow(slide, 2.36, 2.15, 0.25, C.GREEN);
  node(slide, 2.71, 1.90, 1.82, 0.84, 'code 角色会话', '只见知识 + 公开接口\nBubblewrap', { fill: C.NAVY2, accent: C.GREEN, titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 11.2, bodySize: 8.2 });
  arrow(slide, 4.64, 2.15, 0.25, C.GREEN);
  node(slide, 4.99, 1.90, 1.76, 0.84, 'Generated files', '动态路径 enum\nCAS Artifact', { fill: C.NAVY2, accent: C.GREEN, titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 10.7 });
  text(slide, 'Oracle 链 · 不读候选知识', 0.62, 3.40, 3.1, 0.24, { fontSize: 10.2, color: C.PURPLE, bold: true, margin: 0 });
  node(slide, 0.63, 3.90, 1.62, 0.84, '参考源码', 'pinned commit', { fill: C.NAVY2, accent: C.BLUE, titleColor: C.WHITE, bodyColor: C.PALE });
  arrow(slide, 2.36, 4.15, 0.25, C.PURPLE);
  node(slide, 2.71, 3.90, 1.82, 0.84, 'TestGen', '源码 + 公开接口\n不能读候选知识', { fill: C.NAVY2, accent: C.PURPLE, titleColor: C.WHITE, bodyColor: C.PALE });
  arrow(slide, 4.64, 4.15, 0.25, C.PURPLE);
  node(slide, 4.99, 3.90, 1.76, 0.84, 'Oracle validation', '先跑参考实现\n确认测试真值', { fill: C.NAVY2, accent: C.ORANGE, titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 10.4 });
  line(slide, 6.78, 2.32, 1.15, 1.00, C.GREEN, 1.8, true);
  line(slide, 6.78, 4.32, 1.15, -1.00, C.PURPLE, 1.8, true);
  node(slide, 7.98, 2.78, 2.05, 1.10, 'TrustedProjectEvaluator', '独立副本中物化代码\n执行受信命令，采集证据', { fill: C.NAVY3, accent: C.RED, titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 11.2, bodySize: 8.6 });
  arrow(slide, 10.15, 3.15, 0.25, C.RED);
  node(slide, 10.50, 2.78, 2.13, 1.10, 'EvaluationReport', 'tests 1 / 1 · stability 1\ncritical failures 0', { fill: C.NAVY2, accent: C.RED, titleColor: C.WHITE, bodyColor: C.PALE, titleSize: 11.2 });
  box(slide, 0.63, 5.42, 12.00, 0.75, { fill: C.ORANGE, line: C.ORANGE });
  text(slide, 'Bubblewrap 证明模型会话看不到参考源码；它不证明生成代码可安全执行。当前 Evaluator 只允许受信项目，敌对代码沙箱仍未完成。', 0.94, 5.60, 11.40, 0.38, { fontSize: 10.7, color: C.WHITE, bold: true, align: 'center', margin: 0 });
}

// 11 · Review 与知识迭代
{
  const slide = frame('Review 与知识迭代：Agent 提建议，确定性 Gate 才能改状态', 'REVIEW LOOP', '已实现', {
    source: 'automated-project-workflow.ts；src/domain/index.ts；SQLiteFlywheelRepository 发布事务',
  });
  node(slide, 0.63, 2.19, 1.70, 0.94, 'EvaluationReport', '测试事实\n不可变 evidenceRef', { accent: C.RED, fill: C.RED_LIGHT });
  arrow(slide, 2.45, 2.48, 0.26, C.RED);
  node(slide, 2.82, 2.19, 1.62, 0.94, 'Check', '静态阻塞项\n只读', { accent: C.ORANGE, fill: C.ORANGE_LIGHT });
  arrow(slide, 4.56, 2.48, 0.26, C.ORANGE);
  node(slide, 4.93, 2.03, 2.02, 1.26, 'Review 角色', '综合知识、Eval、Check\n给 PASS 建议或 Correction\n不直接决定发布', { accent: C.PURPLE, fill: C.PURPLE_LIGHT, bodySize: 8.8 });
  arrow(slide, 7.07, 2.48, 0.26, C.PURPLE);
  node(slide, 7.44, 2.03, 2.08, 1.26, 'wpKnowledge Gate', '规则绑定 inputRefs\n产生唯一 GateDecision', { accent: C.GREEN, fill: C.GREEN_LIGHT, bodySize: 9 });
  const outcomes = [
    ['PASS', '原子 Publication\n版本 → VERIFIED', C.GREEN],
    ['ITERATE', 'Correction → DocGen\n重写知识再重建', C.ORANGE],
    ['STOPPED', '预算耗尽或基础设施失败\n保留证据', C.RED],
  ];
  outcomes.forEach((o, i) => node(slide, 10.05, 1.34 + i * 1.24, 2.56, 0.83, o[0], o[1], { accent: o[2], fill: i === 0 ? C.GREEN_LIGHT : i === 1 ? C.ORANGE_LIGHT : C.RED_LIGHT, titleSize: 11.3, bodySize: 8.5 }));
  line(slide, 9.56, 2.66, 0.42, -0.78, C.GREEN, 1.3, true);
  line(slide, 9.56, 2.66, 0.42, 0.00, C.ORANGE, 1.3, true);
  line(slide, 9.56, 2.66, 0.42, 1.18, C.RED, 1.3, true);
  box(slide, 0.63, 4.40, 8.89, 1.54, { fill: C.NAVY, line: C.NAVY });
  text(slide, 'Correction 的最小合同', 0.95, 4.69, 2.15, 0.25, { fontSize: 11, color: C.CYAN, bold: true, margin: 0 });
  text(slide, 'correctionId', 3.26, 4.66, 1.42, 0.30, { fontFace: MONO, fontSize: 10.4, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  text(slide, 'knowledgePath', 4.80, 4.66, 1.50, 0.30, { fontFace: MONO, fontSize: 10.4, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  text(slide, 'criterion', 6.43, 4.66, 1.15, 0.30, { fontFace: MONO, fontSize: 10.4, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  text(slide, 'risk', 7.79, 4.66, 0.88, 0.30, { fontFace: MONO, fontSize: 10.4, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  text(slide, '指出知识哪里错、怎样验、风险是什么；不把直接修改代码当成知识治理。', 0.95, 5.17, 7.99, 0.35, { fontSize: 10.2, color: C.PALE, bold: true, align: 'center', margin: 0 });
}

// 12 · 本地问题
{
  const slide = frame('本地运行遇到的问题：真实路径暴露了七个工程缺口', 'RUNTIME ISSUES', '真实证据', {
    dark: true,
    source: '三次 ohMyWorkPanel live Run、Agent 审计与恢复记录；修复均有对应测试',
  });
  const rows = [
    ['01', 'pnpm 路径', '隔离环境只看见链接，找不到真实脚本', '解析真实工具路径，再带入受信评测环境'],
    ['02', '并行状态', '失败分支被晚完成的兄弟节点写回 RUNNING', 'runtime 对并行终态做失败归一化'],
    ['03', 'DSH session', '复用 session 偶发得到空结果', '每次 Provider 尝试使用独立 session'],
    ['04', 'JSON Schema', '模型返回诊断文本、占位字段或非法 JSON', '闭合 Schema + 最多 2 次格式重试；其他错误不重试'],
    ['05', '路径越界', 'code 角色额外生成 mentions.test.ts', 'allowedGeneratedPaths 进入动态 enum，并保留应用层二次校验'],
    ['06', '证据位置', 'Check/Review 误以为工作区缺少生成代码', '明确 CAS 内联上下文，EvaluationReport 是执行事实源'],
    ['07', '安全边界', '角色隔离容易被误写成敌对代码沙箱', '能力分开展示；不可信执行仍 fail closed'],
  ];
  const xs = [0.61, 1.25, 3.25, 7.52];
  const ws = [0.64, 2.00, 4.27, 5.10];
  gridRow(slide, 1.38, ['#', '问题', '真实观察', '收口方式'], xs, ws, { h: 0.42, fill: C.NAVY3, line: '31516E', color: C.WHITE, header: true, fontSize: 9.2, alignments: ['center', 'left', 'left', 'left'] });
  rows.forEach((r, i) => gridRow(slide, 1.86 + i * 0.66, r, xs, ws, {
    h: 0.59, fill: i % 2 === 0 ? C.NAVY2 : '163651', line: '31516E', color: i === 4 ? 'FFD3D0' : 'D4E0EA',
    fontSize: 8.8, firstBold: true, alignments: ['center', 'left', 'left', 'left'],
  }));
  box(slide, 0.61, 6.61, 12.01, 0.32, { fill: C.RED, line: C.RED, label: '工程记录保留失败：否则无法证明恢复、白名单和确定性 Gate 为什么必要。', color: C.WHITE, fontSize: 9.4, bold: true });
}

// 13 · 用户操作
{
  const slide = frame('从用户视角操作：五个动作完成一次可复查治理', 'USER GUIDE', '已实现', {
    source: 'docs/GETTING_STARTED.md；deploy/deepseek-harness/README.md；CLI workflow-run / workflow-report',
  });
  const commands = [
    ['准备来源', '将 ohMyWorkPanel 检出到固定 commit；配置来源 allowlist'],
    ['选择 Provider', 'fixture 用于回归；deepseek-harness 用官方 SDK + Bubblewrap'],
    ['启动治理', 'npm run knowledge -- workflow-run --repository <path> --workers 1 --max-iterations 3'],
    ['查看过程', 'Console 看节点、attempt、事件、评测与 Gate；DSH Web 只调试 Harness'],
    ['导出证据', "npm run knowledge -- workflow-report --run '<run-id>' --output './demo-report.json'"],
  ];
  commands.forEach((c, i) => {
    const y = 1.41 + i * 1.02;
    slide.addShape(pptx.ShapeType.ellipse, { x: 0.68, y: y + 0.10, w: 0.52, h: 0.52, fill: { color: [C.BLUE, C.CYAN, C.PURPLE, C.ORANGE, C.GREEN][i] }, line: { color: [C.BLUE, C.CYAN, C.PURPLE, C.ORANGE, C.GREEN][i] } });
    text(slide, String(i + 1), 0.68, y + 0.15, 0.52, 0.35, { fontSize: 12, color: C.WHITE, bold: true, align: 'center', margin: 0 });
    box(slide, 1.38, y, 11.17, 0.74, { fill: i % 2 === 0 ? C.WHITE : 'EAF1F6', line: C.LINE });
    text(slide, c[0], 1.66, y + 0.10, 1.60, 0.27, { fontSize: 12, color: C.NAVY, bold: true, margin: 0 });
    text(slide, c[1], 3.37, y + 0.09, 8.85, 0.48, { fontFace: i === 2 || i === 4 ? MONO : FONT, fontSize: i === 2 || i === 4 ? 8.5 : 9.8, color: C.MUTED, bold: i === 2 || i === 4, margin: 0 });
  });
  box(slide, 0.68, 6.55, 11.87, 0.35, { fill: C.ORANGE_LIGHT, line: C.ORANGE, label: '凭据只进运行时环境；不要写进仓库、PPT、Issue、示例 .env 或命令历史。', color: C.INK, fontSize: 9.8, bold: true });
}

// 14 · Agent 二次开发
{
  const slide = frame('Agent 二次开发：允许调语气和策略，不允许换掉节点合同', 'AGENT CUSTOMIZATION', '边界', {
    source: 'Agents 页面；AgentCatalogService；agent-definitions.ts；仅 customizableFields=[promptAddon]',
  });
  box(slide, 0.62, 1.41, 4.04, 5.35, { fill: C.WHITE, line: C.LINE });
  addImageContain(slide, AGENT_SHOT, 0.77, 1.56, 3.74, 5.05, 1600, 2319);
  card(slide, 4.98, 1.43, 3.55, 2.14, '可以改', [
    '每个固定角色的 promptAddon（0–4000 字）',
    '后续执行生效，revision 与审计可追踪',
    '例如强调中文术语、引用格式、风险检查重点',
  ], { accent: C.GREEN, bodySize: 9.7 });
  card(slide, 8.83, 1.43, 3.80, 2.14, '不能从前台改', [
    'agentId、节点职责、拓扑和路由',
    '输入输出 JSON Schema、工具与文件权限',
    'Gate、Evaluator 和 Publication authority',
  ], { accent: C.RED, bodySize: 9.7 });
  box(slide, 4.98, 3.92, 7.65, 1.44, { fill: C.NAVY, line: C.NAVY });
  text(slide, '安全的定制流程', 5.28, 4.17, 1.75, 0.25, { fontSize: 11, color: C.CYAN, bold: true, margin: 0 });
  text(slide, '查看固定合同 → 写一段可验证的追加提示 → 在新 Run 试跑 → 对比 Eval / Gate → 保留或清空回滚', 6.93, 4.13, 5.37, 0.47, { fontSize: 10.2, color: C.WHITE, bold: true, align: 'center', margin: 0 });
  box(slide, 4.98, 5.67, 7.65, 0.71, { fill: C.ORANGE_LIGHT, line: C.ORANGE });
  text(slide, '如果要改节点职责、I/O 或权限，这不再是“提示词定制”，而是核心合同变更：必须先改 Spec，再改实现、测试和 PR。', 5.28, 5.84, 7.07, 0.38, { fontSize: 10, color: C.INK, bold: true, align: 'center', margin: 0 });
}

// 15 · 路线图与证据
{
  const slide = frame('下一步：先扩大证据面，再谈生产化与通用项目', 'ROADMAP + EVIDENCE', '下一步', {
    dark: true,
    source: '追踪矩阵：KF-SYS-025 已实现；KF-SYS-003 / NFR-009 仍部分完成；NFR-007 未完成',
  });
  const roadmap = [
    ['P0', '重复 live Run', '同 commit 多次执行，统计成功率、耗时、Token 与失败类型', C.RED],
    ['P0', 'SDK 评测覆盖', '把 1 / 1 扩成前端全测、构建和 Rust 测试；保留 Headless 295 / 295 对照', C.RED],
    ['P1', '语义分块', 'symbol / dependency graph、SCC、动态 worker、增量合并与覆盖 Gate', C.ORANGE],
    ['P1', '敌对代码沙箱', 'CPU / 内存 / 网络 / 系统调用 / 输出预算；未完成前只跑受信项目', C.ORANGE],
    ['P2', '通用项目向导', '把固定 profile 演进为显式策略、来源、语言插件和评测配置', C.PURPLE],
  ];
  roadmap.forEach((r, i) => {
    const y = 1.40 + i * 0.94;
    pill(slide, r[0], 0.62, y + 0.19, 0.62, r[3], { fontSize: 8 });
    box(slide, 1.42, y, 11.18, 0.75, { fill: C.NAVY2, line: '31516E' });
    text(slide, r[1], 1.72, y + 0.10, 2.12, 0.25, { fontSize: 11.5, color: C.WHITE, bold: true, margin: 0 });
    text(slide, r[2], 3.92, y + 0.08, 8.33, 0.46, { fontSize: 9.5, color: C.PALE, margin: 0 });
  });
  box(slide, 0.62, 6.28, 12.00, 0.50, { fill: C.NAVY3, line: '31516E' });
  text(slide, '证据入口：三次运行记录 · 两份脱敏 JSON · 深/浅色 Console 截图 · 可编辑 PPT 源文件', 0.91, 6.40, 11.42, 0.27, { fontSize: 10.1, color: C.CYAN, bold: true, align: 'center', margin: 0 });
}

await pptx.writeFile({ fileName: OUT });
