# Knowledge Repository Layout

## Boundary

`endlessWpKnowledgeRunner/` is executable code and integration code. The
repository-level `knowledge/` directory is the OKF knowledge base. The runner
is configured with `knowledge_dir: ../knowledge`; it never treats its own
source tree as the knowledge store.

```text
wpKnowledge/
├─ endlessWpKnowledgeRunner/       # runner, CLI, DSH adapter, Dashboard
│  ├─ fwrunner/                    # deterministic pipeline and Store API
│  ├─ dsh/                         # optional DSH adapter
│  ├─ web/                         # local Dashboard
│  └─ tests/
└─ knowledge/                      # published OKF bundle
   ├─ inbox/                       # controlled acquisition input
   ├─ drafts/                      # below-gate candidates
   ├─ concepts/                    # verified retrieval corpus
   ├─ history/<concept>/           # prior verified snapshots
   ├─ schema/                      # format contract
   ├─ index.md                     # generated catalog
   └─ runtime/                     # ledger, log, cursor, jury output
```

## Write policy

There is one insertion path:

```text
agent/user/adapter -> fw.py ingest -> OKF normalize -> score -> gate
                       -> knowledge/drafts or knowledge/concepts
                       -> history/index/runtime updates
```

`inbox/` accepts raw Markdown only. An agent must not write a card directly to
`concepts/` or change `verified` in frontmatter. `Store.write_card()` validates
the schema, status-directory match, source presence, version, and safe concept
name, then uses a temporary file plus replace so readers never see a partial
card. Index, ledger, and live-mode state use the same atomic-write path.

## Version and gate invariants

1. A new concept starts at version 1.
2. A verified revision snapshots the old card under `history/<name>/vN.md`
   before publishing version `N+1`.
3. A below-gate revision is stored as a draft and cannot replace the verified
   card.
4. Retrieval defaults to `concepts/`; drafts are opt-in for inspection.
5. `runtime/` is governance evidence and is never scanned as an input source.

This layout separates publishable knowledge from implementation and from
mutable runtime state while keeping every published card human-readable and
Git-reviewable.
