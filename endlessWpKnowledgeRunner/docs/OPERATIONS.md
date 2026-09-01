# Knowledge Flywheel operations

## Local initialization

```powershell
npm install
npm run knowledge -- init
npm run knowledge -- migrate-legacy --root knowledge
npm run knowledge -- scan
npm run knowledge -- list --status CANDIDATE
```

Use `WP_FLYWHEEL_HOME` to place SQLite/CAS outside the default `.workpanel/` directory.

## Add a candidate

```powershell
npm run knowledge -- ingest `
  --module example-module `
  --file knowledge/inbox/example.md `
  --source knowledge/inbox/example.md `
  --source-commit <commit> `
  --pinned `
  --title "Example knowledge" `
  --description "Why this knowledge is reusable"
```

The result contains a `quality` report and a KnowledgeVersion whose status is still `CANDIDATE`.

## Behavioral evaluation and publication

The general `evaluate` command remains a trusted report-ingestion adapter: it records supplied evidence but does not launch a process. Operators must only submit results produced by an independently controlled evaluator.

```powershell
npm run knowledge -- create-run --module example-module --policy local-v1
npm run knowledge -- transition --run <run-id> --state PLANNED
npm run knowledge -- transition --run <run-id> --state GENERATING
npm run knowledge -- transition --run <run-id> --state EVALUATING

npm run knowledge -- evaluate `
  --run <run-id> `
  --version <version-id> `
  --toolchain "cpp-plugin@1;compiler=<exact-version>" `
  --tests-passed 12 `
  --tests-total 12 `
  --critical-failures 0 `
  --stability 1 `
  --evidence-file <test-report.json>

npm run knowledge -- publish `
  --run <run-id> `
  --version <version-id> `
  --decision <pass-decision-id>
```

Recording an evaluation atomically stores the report and Gate decision while moving the run from `EVALUATING` to `REVIEWING`; this applies equally to CLI and HTTP callers. An exact retry returns the original report and decision without adding events, while a retry with different inputs fails closed as a replay collision. The CLI rejects publication when the decision is not PASS, evidence belongs to another run/version, provenance is absent, or the body artifact fails integrity verification.

## Fixed-commit real-source acceptance

The project acceptance command exercises the full two-iteration flow against a clean archive of a pinned ohMyWorkPanel commit. It proves the reference gate, an intentionally failing first generation, structured Correction, incremental knowledge revision, fresh code generation, independent process evaluation, deterministic PASS and idempotent publication.

```powershell
npm run acceptance:ohmyworkpanel -- `
  --repository D:\AI\LinlisWorkPanel `
  --runtime D:\temp\wp-ohmy-acceptance `
  --output summary
```

The source repository must contain the exact commit pinned in `endlessWpKnowledgeRunner/acceptance/ohmyworkpanel/scenario.json`; a missing or non-exact object fails closed. The current branch may advance: the report distinguishes its checkout HEAD from the archived acceptance commit and never checks out or modifies either. The evaluator uses `git archive`, writes generated files only into a temporary directory, permits only `node`, `pnpm` and `cargo`, avoids shell execution, sanitizes inherited environment variables, enforces command timeout/output limits, and stores tool versions, redacted argv, exit status and redacted output in CAS. The checked-in Agent provider replays schema-validated fixtures, so this command validates orchestration and execution—not live GLM/DeepSeek quality. It is also not an OS sandbox; run it only against trusted source and generated code.

## Legacy Runner compatibility

Existing automation can invoke `node endlessWpKnowledgeRunner/fw.mjs`. Supported commands delegate directly to the new CLI and share `WP_FLYWHEEL_HOME`; `--root` is rejected so callers cannot accidentally select a parallel store. Removed score/eval/harvest semantics fail explicitly. See `endlessWpKnowledgeRunner/README.md` for the mapping.

## Dashboard and API

```powershell
$env:WP_KNOWLEDGE_WRITE_TOKEN = '<local-secret>'
npm run knowledge:serve
```

Open `http://127.0.0.1:4174`. Read endpoints do not require credentials. Mutation endpoints require `Authorization: Bearer <local-secret>`; with no configured token, writes return `503 WRITE_API_DISABLED`.

For an explicitly public, read-only deployment, override the configured listener without enabling the write token:

```bash
WP_KNOWLEDGE_HOST=0.0.0.0 WP_KNOWLEDGE_PORT=80 npm run knowledge:serve
```

Then open `http://<server-public-ip>/`. The cloud security group must allow inbound TCP traffic to the selected port. Prefer restricting the source CIDR to the operator's IP; do not expose mutation endpoints over plain HTTP. Use a TLS reverse proxy before enabling `WP_KNOWLEDGE_WRITE_TOKEN` on any non-local interface.

The product console provides Overview, Runs, Knowledge, Governance, Evidence and Settings views. Run observation uses `GET /api/v1/runs`, `GET /api/v1/runs/:runId` and the ordered event tail at `GET /api/v1/runs/:runId/events?after=<event-seq>`. The browser remains read-only by default; the operator token is held only in current-page memory and is currently used by the feedback form. Generic automatic Run start is intentionally disabled until the server-side Workflow Command API exists; the browser never simulates orchestration by chaining raw transition calls.

The stable local API prefix is `/api/v1`. `/health` remains unversioned for process probes.

## DSH

Mount `packages/adapters/dsh/src/index.ts` as a normal Cordis plugin and configure:

```text
WP_KNOWLEDGE_URL=http://127.0.0.1:4174
WP_KNOWLEDGE_WRITE_TOKEN=<local-secret>
```

The adapter registers `wp_knowledge_query`, `wp_knowledge_status`, `wp_knowledge_scan`, `wp_knowledge_ingest_candidate` and `wp_knowledge_feedback`. It has no shell dependency and cannot publish knowledge. Scan roots are fixed in `runner.config.json`; callers cannot request arbitrary filesystem paths.

## GitHub Pages project site

The project website is a separate static surface. It explains the product and links to documentation, but never connects to the local Registry or mutation API.

```bash
npm run site:check
npm run site:serve
```

Open <http://127.0.0.1:4175>. After merge to `main`, `.github/workflows/pages.yml` publishes `endlessWpKnowledgeRunner/site/`. A repository administrator must select **GitHub Actions** as the Pages source once in Settings → Pages. The expected public URL is <https://linlisworkteam.github.io/wpKnowledge/>.
