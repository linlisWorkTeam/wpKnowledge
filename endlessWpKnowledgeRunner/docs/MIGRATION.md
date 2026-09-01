# Migration from `endlessWpKnowledgeRunner`

## What changed

The old Python system mixed ingestion, document scoring, state, storage, feedback, scheduling, DSH shell execution and Dashboard writes. It also encoded state in directories/frontmatter and promoted high-scoring documents directly to `verified`.

The replacement separates those responsibilities into domain, application, port and adapter packages. SQLite/CAS is now canonical runtime state. `knowledge/` remains a Git-reviewed source and import format.

## One-time import

1. Keep the existing `knowledge/` tree under version control.
2. Use an empty runtime directory or back up `.workpanel/`.
3. Run:

```powershell
npm install
npm run knowledge -- migrate-legacy --root knowledge
npm run knowledge -- status
```

The importer uses the maintained `yaml` package. It imports cards from `knowledge/concepts/` and `knowledge/drafts/`, preserves old status/version metadata, and sets `requiresBehavioralVerification: true`. A former `verified` card remains `CANDIDATE` until a new run supplies real execution evidence and receives a PASS decision.

The import is idempotent: `moduleId + body artifact` resolves to the existing KnowledgeVersion on replay.

## Verified publication

Create a run, advance it to `EVALUATING`, attach an immutable test report, then publish using its PASS decision. See `OPERATIONS.md` for the command sequence.

## Rollback

Before cutover, preserve the old Git commit and runtime directory. The new runtime is isolated under `.workpanel/`; deleting that local directory returns the repository to a pre-import runtime state without modifying `knowledge/`.

Do not restore the former `verified` meaning after rollback. It represented document-quality acceptance, not behavioral verification.
