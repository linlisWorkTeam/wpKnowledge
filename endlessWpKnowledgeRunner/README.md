# endlessWpKnowledgeRunner compatibility facade

This directory preserves the established Runner entrypoint while delegating every supported operation to the repository's TypeScript Knowledge Flywheel. It owns no store, quality authority, HTTP server, timer, Python package, or DSH shell bridge.

The productized browser assets live in `web/`; `apps/runner/src/server.ts` remains the HTTP adapter and serves those assets without moving Registry, Gate, workflow, or publication authority into this compatibility directory.

```powershell
node endlessWpKnowledgeRunner/fw.mjs init
node endlessWpKnowledgeRunner/fw.mjs ingest --file knowledge/inbox/example.md --name example --source knowledge/inbox/example.md --pinned
node endlessWpKnowledgeRunner/fw.mjs query --q "example"
node endlessWpKnowledgeRunner/fw.mjs status
```

`init`, `ingest`, `query`, `get`, `status`, `scan`, and `feedback` map to the versioned core CLI. Legacy `verified` maps to `VERIFIED`; legacy `draft` maps to `CANDIDATE`. `--force-draft` is redundant because ingestion can only create candidates.

`score`, `eval`, and `harvest` fail with migration guidance. Their previous semantics either treated document quality as publication authority or relied on non-recoverable timer state. Use the real-source workflow and independent EvalRunner for behavioral verification. Set `WP_FLYWHEEL_HOME` to choose the shared SQLite/CAS runtime location; the removed `--root` flag is intentionally not reinterpreted.

## Specifications

The Runner-facing [product specification](specs/README.md), [frontend product design](specs/04-product/frontend-product-design.md), use cases, actor boundaries, supported entry points, and interaction sequences live under `endlessWpKnowledgeRunner/specs/`. The repository-level `specs/` directory remains the normative source for shared domain, gate, security, and acceptance contracts.
