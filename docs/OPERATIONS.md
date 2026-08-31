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

The current `evaluate` command is a trusted local adapter: it records a report and commits the supplied evidence file to CAS, but it does not run a compiler or test process. Operators must only submit results produced by an independently controlled evaluator. Keep production publication disabled until the planned EvalRunner and hostile-code sandbox are implemented and validated.

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

The CLI rejects publication when the decision is not PASS, evidence belongs to another run/version, provenance is absent, or the body artifact fails integrity verification.

## Dashboard and API

```powershell
$env:WP_KNOWLEDGE_WRITE_TOKEN = '<local-secret>'
npm run knowledge:serve
```

Open `http://127.0.0.1:4174`. Read endpoints do not require credentials. Mutation endpoints require `Authorization: Bearer <local-secret>`; with no configured token, writes return `503 WRITE_API_DISABLED`.

The stable local API prefix is `/api/v1`. `/health` remains unversioned for process probes.

## DSH

Mount `packages/adapters/dsh/src/index.ts` as a normal Cordis plugin and configure:

```text
WP_KNOWLEDGE_URL=http://127.0.0.1:4174
WP_KNOWLEDGE_WRITE_TOKEN=<local-secret>
```

The adapter registers `wp_knowledge_query`, `wp_knowledge_status`, `wp_knowledge_scan`, `wp_knowledge_ingest_candidate` and `wp_knowledge_feedback`. It has no shell dependency and cannot publish knowledge. Scan roots are fixed in `workpanel.config.json`; callers cannot request arbitrary filesystem paths.
