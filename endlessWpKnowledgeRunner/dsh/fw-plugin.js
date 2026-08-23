// ============================================================================
// endlessWpKnowledgeRunner — DSH Host plugin (endless knowledge flywheel)
//
// Loads the flywheel MVP onto DeepSeek Harness as:
//   - model tools:    fw_ingest / fw_query / fw_get / fw_score / fw_eval /
//                     fw_status / fw_scan / fw_feedback / fw_livemode / fw_harvest
//   - liveMode:       timer-driven harvest cycles; on enable, a harvester
//                     *agent* (subagent) extracts knowledge from candidates
//                     and the deterministic OKF pipeline scores + gates it
//   - HTTP endpoints: GET /fw/query, GET /fw/status (external retrieval)
//
// The plugin is a thin wrapper: all flywheel logic lives in the Python core
// (`../fw.py` + `fwrunner/`), one language, one source of truth. This file is
// exactly the `code.host` body passed to cordis_define.
// ============================================================================

return {
  inject: ['timer'],
  apply(ctx) {
    const timer = ctx.timer
    const shell = ctx.get('shell')
    const subagents = ctx.get('subagents')
    const webServer = ctx.get('webServer')
    const sandboxPolicySvc = ctx.get('sandboxPolicy')
    const RUNNER_ROOT = 'D:/AI/wpKnowledge/endlessWpKnowledgeRunner'

    // ---------------------------------------------------------------- helpers
    function q(arg) {
      const s = String(arg == null ? '' : arg)
      return /[ \t"]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
    }

    async function runFw(args, opts) {
      if (!shell) throw new Error('fw: shell service is not mounted')
      const o = opts || {}
      const cmd = 'python fw.py ' + args.map(q).join(' ')
      const request = {
        command: cmd,
        workdir: RUNNER_ROOT,
        timeoutMs: o.timeoutMs || 180000,
        env: { PYTHONIOENCODING: 'utf-8' },
      }
      // The runner writes to its store; resolve an explicit policy so the
      // Python process is not confined to 'read-only' by the shell default.
      // Threading the calling agent's session gives workspace-write the
      // correct boundary (the session cwd).
      if (sandboxPolicySvc) {
        const req = { mode: 'workspace-write' }
        const agent = o.agent
        if (agent && agent.session) req.session = agent.session
        const policy = sandboxPolicySvc.resolve(req)
        if (policy) request.sandboxPolicy = policy
      }
      if (o.stdin !== undefined) request.stdin = o.stdin
      const spec = shell.resolve(request)
      const res = await shell.run(spec)
      const outText = (col) => (col && typeof col.text === 'string') ? col.text : ''
      const stderr = outText(res.stderr)
      const stdout = outText(res.stdout)
      if (res.exitCode !== 0) {
        const msg = String(stderr || stdout || ('exit ' + res.exitCode)).trim()
        throw new Error('fw: ' + msg)
      }
      const text = String(stdout).trim()
      if (!text) return null
      const start = text.indexOf('{')
      return JSON.parse(start > 0 ? text.slice(start) : text)
    }

    function render(args, value) {
      return [{ type: 'text', text: JSON.stringify(value) }]
    }

    // -------------------------------------------------------------- liveMode
    const livemode = { timer: null, agent: null, signal: null, withAgent: true, maxCycle: 4 }

    const HARVEST_PROMPT = function (candPath) {
      return '你是 wpKnowledge 知识飞轮的 harvest agent（获取环节）。\n'
        + '任务：读取来源文件 ' + candPath + '，从中提炼一条可复用、可验证的知识，返回结构化 JSON。\n'
        + '要求：\n'
        + '1. content 必须是解释型 Markdown（四节：## 概述 / ## 设计要点（伪代码或要点 + 为什么）/ ## 适用场景 / ## 验证）；\n'
        + '2. 保留逻辑的"魂"（边界处理、数据结构、调用关系），禁止整段搬运原文，宁缺毋滥；\n'
        + '3. 内容太差或纯噪音时 content 返回空字符串，不要硬造知识；\n'
        + '4. name 用英文短横线 id（如 workpanel-connecter），description 一句话概括；\n'
        + '5. sources 的 path 用仓库内相对路径（相对 D:/AI/wpKnowledge），lines 尽量给出。'
    }

    const HARVEST_SCHEMA = {
      type: 'object',
      additionalProperties: false,
      properties: {
        name: { type: 'string', required: true },
        title: { type: 'string' },
        description: { type: 'string', required: true },
        category: { type: 'string' },
        tags: { type: 'array', items: { type: 'string' } },
        content: { type: 'string', required: true },
        sources: {
          type: 'array',
          items: {
            type: 'object',
            additionalProperties: false,
            properties: {
              path: { type: 'string' },
              lines: { type: 'string' },
            },
          },
        },
      },
    }

    async function extractWithAgent(cand, cycleSignal, agent) {
      if (!subagents || !agent) return null
      if (livemode.signal && livemode.signal.aborted) return null
      const providers = typeof subagents.list === 'function' ? subagents.list() : []
      const provider = providers[0] || 'in-process'
      const run = await subagents.start(provider, {
        label: 'fw-harvester:' + cand.path,
        prompt: [{ type: 'text', text: HARVEST_PROMPT(cand.path) }],
        parent: agent,
        signal: cycleSignal,
        outputSchema: HARVEST_SCHEMA,
      })
      const result = await run.result
      return result && result.structured ? result.structured : null
    }

    async function runCycle(cycleSignal, agent) {
      const results = []
      const scan = await runFw(['scan', '--json'], { agent })
      const candidates = (scan && scan.candidates) || []
      for (let i = 0; i < Math.min(candidates.length, livemode.maxCycle); i++) {
        const cand = candidates[i]
        try {
          let extracted = null
          if (livemode.withAgent) {
            try {
              extracted = await extractWithAgent(cand, cycleSignal, agent)
            } catch (e) {
              extracted = null
            }
          }
          if (extracted && extracted.content) {
            const args = ['ingest', '--json', '--name', extracted.name || '',
              '--title', extracted.title || '', '--description', extracted.description || '',
              '--category', extracted.category || '',
              '--tags', (extracted.tags || []).join(','),
              '--source', cand.path, '--pinned']
            const srcLines = ((extracted.sources || [])[0] || {}).lines
            if (srcLines) args.push('--source-lines', srcLines)
            const res = await runFw(args, { stdin: extracted.content, agent })
            results.push({ path: cand.path, extracted: true, result: res })
          } else {
            const res = await runFw(['ingest', '--json', '--file', cand.path, '--source', cand.path, '--pinned'], { agent })
            results.push({ path: cand.path, extracted: false, result: res })
          }
        } catch (e) {
          results.push({ path: cand.path, error: String((e && e.message) || e) })
        }
      }
      return { total: (scan && scan.total) || 0, consumed: results.length, results }
    }

    // ---------------------------------------------------------------- tools
    const tools = []

    tools.push(harness.defineTool({
      name: 'fw_ingest',
      description: '知识飞轮【触发式获取】入口：把一段知识（Markdown 文本或文件）推入飞轮。'
        + '管道会自动完成 OKF 沉淀（frontmatter/sources）、多信号打分、门禁判定：'
        + 'score >= 门禁阈值(默认70) -> verified 合并入 store/concepts/，否则留在 store/drafts/ 并返回薄弱点。'
        + '使用场景：有人/agent 向知识库推知识、修订已有概念（自动版本升级+历史快照）。',
      parameters: {
        content: { type: 'string', description: '知识正文（解释型 Markdown：概述/设计要点+为什么/适用场景/验证）。与 file 二选一。' },
        file: { type: 'string', description: '知识文件路径（相对 endlessWpKnowledgeRunner 根目录，或绝对路径）。与 content 二选一。' },
        name: { type: 'string', description: '概念 id（英文短横线）。缺省从 frontmatter/文件名/首个 H1 推断。' },
        title: { type: 'string', description: '展示标题' },
        description: { type: 'string', description: '一句话描述' },
        category: { type: 'string', description: '分类，如 architecture / knowledge-format' },
        tags: { type: 'array', items: { type: 'string' }, description: '标签列表' },
        source: { type: 'string', description: '溯源路径（仓库内相对路径或 URL），会写入知识卡 sources 字段' },
        pinned: { type: 'boolean', description: '标记 sources 为 pinned（有 file:line / commit / url 锚点）' },
        force_draft: { type: 'boolean', description: '强制留在 drafts 不过门禁（调试用）' },
      },
      output: {
        schema: {
          type: 'object', additionalProperties: true,
          properties: {
            concept: { type: 'string', required: true },
            status: { type: 'string', required: true },
            score: { type: 'number', required: true },
            gate: { type: 'string', required: true },
            note: { type: 'string' },
            report: { type: 'json' },
          },
        },
        render,
      },
      async execute(args, exec) {
        const a = ['ingest']
        if (args.file) a.push('--file', args.file)
        if (args.name) a.push('--name', args.name)
        if (args.title) a.push('--title', args.title)
        if (args.description) a.push('--description', args.description)
        if (args.category) a.push('--category', args.category)
        if (args.tags) a.push('--tags', args.tags.join(','))
        if (args.source) a.push('--source', args.source)
        if (args.pinned) a.push('--pinned')
        if (args.force_draft) a.push('--force-draft')
        a.push('--json')
        if (args.content) {
          return runFw(a, { stdin: args.content, agent: exec.agent })
        }
        return runFw(a, { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_query',
      description: '知识飞轮【应用】环节：只读检索 OKF 知识库（BM25 + 质量重排，无 RAG）。'
        + '返回 top-k 命中（name/score/sources/snippet）。每次命中会记录 usage 信号回流评测。'
        + '外部系统也可通过 HTTP: GET http://127.0.0.1:3080/fw/query?q=... 检索。',
      parameters: {
        q: { type: 'string', required: true, description: '检索词（支持中英文混合，如 "connecter 适配层"）' },
        top: { type: 'number', description: '返回条数，默认 8' },
        status: { type: 'string', description: '只搜 verified 或 draft' },
        category: { type: 'string', description: '按 category 过滤' },
        platform: { type: 'string', description: '按 platforms 过滤' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { hits: { type: 'array' }, total: { type: 'number' } } },
        render,
      },
      async execute(args, exec) {
        const a = ['query', '--q', args.q, '--json']
        if (args.top) a.push('--top', String(args.top))
        if (args.status) a.push('--status', args.status)
        if (args.category) a.push('--category', args.category)
        if (args.platform) a.push('--platform', args.platform)
        return runFw(a, { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_get',
      description: '按概念 id 取回一张 OKF 知识卡（含 sources 与正文摘要）。',
      parameters: { name: { type: 'string', required: true, description: '概念 id' } },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { name: { type: 'string', required: true } } },
        render,
      },
      async execute(args, exec) {
        return runFw(['get', '--json', '--name', args.name], { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_score',
      description: '知识飞轮【评测】环节：对单个或全部概念重新打分（多信号：溯源/结构/时效/去重/可验证性/使用反馈），'
        + '返回信号分 + 薄弱点清单。分数落回知识卡 frontmatter。',
      parameters: {
        name: { type: 'string', description: '概念 id；缺省配合 all=true' },
        all: { type: 'boolean', description: '对全部概念重新打分' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { concept: { type: 'string' } } },
        render,
      },
      async execute(args, exec) {
        if (args.all) return runFw(['score', '--json', '--all'], { agent: exec.agent })
        if (!args.name) throw new Error('fw_score 需要 name 或 all=true')
        return runFw(['score', '--json', '--name', args.name], { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_eval',
      description: '可靠性评测（Fragility 约束）：对概念重复打分 --runs 次，报告均值±方差与稳定性。'
        + '单次评测的提升不可信，必须看多次重复结果。',
      parameters: {
        name: { type: 'string', description: '概念 id' },
        runs: { type: 'number', description: '重复次数，默认 3，建议 >=5' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { mean: { type: 'number' }, std: { type: 'number' } } },
        render,
      },
      async execute(args, exec) {
        return runFw(['eval', '--json', '--name', args.name || '', '--runs', String(args.runs || 3)], { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_status',
      description: '飞轮仪表盘：概念总数/verified/drafts 数量、平均分、库内最近日志。',
      parameters: {},
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' } } },
        render,
      },
      async execute(args, exec) {
        return runFw(['status', '--json'], { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_scan',
      description: 'liveMode 扫描：列出 sources/ 与 watch_dirs 中新增/变更且未入库的候选文件。',
      parameters: {},
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { candidates: { type: 'array' } } },
        render,
      },
      async execute(args, exec) {
        return runFw(['scan', '--json'], { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_feedback',
      description: '记录使用反馈（应用→评测回流）：hit/rate/correct。usage 信号会参与打分。',
      parameters: {
        name: { type: 'string', required: true, description: '概念 id' },
        action: { type: 'string', required: true, enum: ['hit', 'rate', 'correct'], description: '命中/评分/勘误' },
        rating: { type: 'number', description: 'action=rate 时的 1-5 分' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { entry: { type: 'json' } } },
        render,
      },
      async execute(args, exec) {
        const a = ['feedback', '--json', '--name', args.name, '--action', args.action]
        if (args.rating != null) a.push('--rating', String(args.rating))
        return runFw(a, { agent: exec.agent })
      },
    }))

    tools.push(harness.defineTool({
      name: 'fw_livemode',
      description: '知识飞轮【自动化获取】：开启/关闭 liveMode。开启时立即执行一轮 harvest，'
        + '此后每 interval_minutes 分钟自动扫描：新候选由 harvester agent 提炼知识后走同一条打分门禁。'
        + 'with_agent=false 时为确定性模式（无 agent，直接 ingest 原文）。',
      parameters: {
        enable: { type: 'boolean', required: true, description: 'true 开启，false 关闭' },
        interval_minutes: { type: 'number', description: '扫描间隔（分钟），默认 15' },
        max_cycle: { type: 'number', description: '每轮最多处理候选数，默认 4' },
        with_agent: { type: 'boolean', description: '是否用 harvester agent 提炼，默认 true' },
        run_now: { type: 'boolean', description: 'enable=true 时是否立即 harvest 一轮，默认 true' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, live: { type: 'boolean' } } },
        render,
      },
      async execute(args, exec) {
        if (args.enable) {
          if (livemode.timer) return { ok: true, live: true, note: 'liveMode 已在运行', interval_minutes: args.interval_minutes || 15 }
          livemode.agent = exec.agent
          livemode.signal = exec.signal
          livemode.withAgent = args.with_agent !== false
          livemode.maxCycle = args.max_cycle || 4
          const intervalMin = args.interval_minutes || 15
          const first = args.run_now === false ? null : await runCycle(exec.signal, exec.agent)
          livemode.timer = timer.interval(() => {
            runCycle(livemode.signal, livemode.agent).catch((e) => {
              console.log('[fw-livemode] cycle error:', String((e && e.message) || e))
            })
          }, Math.max(1, intervalMin) * 60 * 1000)
          return { ok: true, live: true, interval_minutes: intervalMin, first_cycle: first }
        }
        if (livemode.timer) {
          livemode.timer()
          livemode.timer = null
        }
        livemode.agent = null
        livemode.signal = null
        return { ok: true, live: false }
      },
    }))

    // fw_harvest: one agent-driven cycle on demand (the liveMode tick body).
    tools.push(harness.defineTool({
      name: 'fw_harvest',
      description: '立即执行一轮 harvest：扫描候选 → harvester agent 提炼 → ingest（打分+门禁）。'
        + 'liveMode 的每个 tick 就是这个动作；也可以手动触发。',
      parameters: {
        with_agent: { type: 'boolean', description: '是否用 harvester agent 提炼，默认 true' },
        max_cycle: { type: 'number', description: '本轮最多处理候选数，默认 4' },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { total: { type: 'number' } } },
        render,
      },
      async execute(args, exec) {
        const prevAgent = livemode.agent
        const prevSignal = livemode.signal
        const prevWithAgent = livemode.withAgent
        const prevMax = livemode.maxCycle
        livemode.agent = exec.agent
        livemode.signal = exec.signal
        livemode.withAgent = args.with_agent !== false
        livemode.maxCycle = args.max_cycle || 4
        try {
          return await runCycle(exec.signal, exec.agent)
        } finally {
          livemode.agent = prevAgent
          livemode.signal = prevSignal
          livemode.withAgent = prevWithAgent
          livemode.maxCycle = prevMax
        }
      },
    }))

    for (const tool of tools) {
      harness.registerTool(ctx, tool)
    }

    // ------------------------------------------------- HTTP external retrieval
    // NOTE: registrations MUST be fiber-owned (ctx.effect) so stop/undefine
    // disposes them; a bare webServer.register would leak until process end.
    // Paths default to /flywheel/*: they never collide with a stale /fw/*
    // registration left by an older package in the same process.
    if (webServer) {
      const queryHandler = async (req, res) => {
        try {
          const raw = (req.url || '').split('?')[1] || ''
          const params = {}
          for (const pair of raw.split('&')) {
            if (!pair) continue
            const [k, v] = pair.split('=')
            params[decodeURIComponent(k)] = decodeURIComponent(v || '')
          }
          const data = await runFw(['query', '--q', params.q || '', '--top', params.top || '5', '--no-feedback', '--json'])
          res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
          res.end(JSON.stringify(data))
        } catch (e) {
          res.writeHead(500, { 'content-type': 'application/json; charset=utf-8' })
          res.end(JSON.stringify({ error: String((e && e.message) || e) }))
        }
      }
      const statusHandler = async (req, res) => {
        try {
          const data = await runFw(['status', '--json'])
          res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' })
          res.end(JSON.stringify(data))
        } catch (e) {
          res.writeHead(500, { 'content-type': 'application/json; charset=utf-8' })
          res.end(JSON.stringify({ error: String((e && e.message) || e) }))
        }
      }
      ctx.effect(() => webServer.register({ kind: 'exact', path: '/flywheel/query', handler: queryHandler }))
      ctx.effect(() => webServer.register({ kind: 'exact', path: '/flywheel/status', handler: statusHandler }))
      console.log('[fw] HTTP endpoints ready: /flywheel/query?q=..., /flywheel/status')
    }

    console.log('[fw] endlessWpKnowledgeRunner plugin active; tools: fw_ingest fw_query fw_get fw_score fw_eval fw_status fw_scan fw_feedback fw_livemode fw_harvest')
  },
}