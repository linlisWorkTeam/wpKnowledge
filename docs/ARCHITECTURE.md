# Knowledge Flywheel architecture

## Boundary

The runtime uses a hexagonal dependency direction:

```text
DSH / CLI / HTTP / future LangGraph
                 │
                 ▼
           Application services
                 │
        ┌────────┴────────┐
        ▼                 ▼
      Domain            Ports
                          ▲
          SQLite/CAS / Agent / Sandbox / Language adapters
```

`packages/domain` imports no workflow SDK, database, model provider, compiler, or language-specific type. `packages/application` depends only on the domain and ports. Architecture tests enforce these rules.

`endlessWpKnowledgeRunner/fw.mjs` is a compatibility facade at the CLI edge. The same component owns Runner-facing product specs, browser assets, the HTTP adapter, and a read-only console projection. `apps/runner/src/server.ts` is only its established launch/import facade. All write paths still delegate to the shared application services and therefore cannot own a second registry, lifecycle, score, workflow, or publication authority.

## Knowledge lifecycle

1. Ingestion commits Markdown bytes to CAS and creates a `CANDIDATE` version in SQLite.
2. The deterministic Quality Gate reports structure, provenance, verification anchors and substance. `ACCEPTED` means the candidate is suitable for behavioral evaluation; it does not mean correct.
3. A run moves through explicit monotonic states. An `EvaluationReport` binds test totals, critical failures, stability, toolchain fingerprint and immutable evidence artifacts. The report, Gate decision, review transition and their events commit in one transaction; an identical retry replays the same persisted result and a conflicting retry is rejected.
4. The deterministic Gate returns `PASS`, `ITERATE`, `ROLLBACK` or `STOPPED`.
5. Publication verifies CAS integrity and performs one SQLite transaction that updates the run, supersedes the previous verified version, verifies the new version, appends the event and creates the publication receipt.

The real-source acceptance slice adds a `ProjectEvaluator` port. Its trusted local adapter resolves and archives an exact Git commit into a temporary workspace without changing the repository's current checkout, applies generated files only there, executes allowlisted tools without a shell, and commits the complete process evidence to CAS. DocGen/CodeGen/Review outputs are independently JSON-Schema validated; the checked-in scenario provider is deterministic test infrastructure, not evidence of live-model quality.

## Persistence

- Artifact ID is `sha256:<digest>` and must match the content digest.
- CAS writes a temporary object, flushes it, renames it and verifies the committed bytes.
- SQLite uses WAL and `synchronous=FULL`.
- State, events, gate decisions and publication pointers are committed transactionally.
- A `GenerationKey` identifies a node side effect. Re-execution returns the committed checkpoint output; a concurrent duplicate fails closed while the first execution is running, and a recorded failure may be retried without losing its retry count or event history.
- Publication key is `moduleId:versionId:policyId`; repeated publication returns the existing receipt.

## Security boundary

- Versioned `/api/v1` HTTP GET operations are read-only.
- HTTP mutation is disabled unless `WP_KNOWLEDGE_WRITE_TOKEN` is configured and every request supplies the bearer token.
- The token is a local trusted-operator boundary, not a complete subject/resource/action authorization matrix. The current evaluation endpoint records and validates submitted evidence metadata; it does not itself compile or execute code.
- DSH accesses the versioned HTTP API and never launches Python or a shell.
- The trusted project evaluator sanitizes its environment, rejects path traversal and symlink targets, caps time/output, and terminates process trees. These controls protect an acceptance run from accidental damage; a child process still shares the host kernel and is not safe for hostile code.
- The core separately defines a Sandbox port. Until a real OS isolation adapter passes escape, network, filesystem and resource tests, untrusted C++ execution must fail closed.

## Runtime requirement

Node.js 24 or newer is required because the local adapter uses the built-in `node:sqlite` API. The repository pins the only third-party runtime dependency (`yaml`) for one-time legacy OKF migration; normal storage uses JSON columns and CAS rather than YAML parsing.
