# Knowledge Base

This directory is the published knowledge base. It is intentionally separate
from `endlessWpKnowledgeRunner/`, which contains the flywheel implementation.

## Directory contract

| Path | Responsibility | Writer |
|---|---|---|
| `inbox/` | Raw Markdown candidates waiting for ingestion | human or acquisition adapter |
| `drafts/` | OKF cards that have not passed the gate | runner only |
| `concepts/` | Verified cards available to retrieval | runner only; reviewed through Git |
| `history/<name>/` | Immutable snapshots of prior verified versions | runner only |
| `schema/` | Card format and governance contract | repository maintainers |
| `index.md` | Generated catalog of cards and sources | runner only |
| `runtime/` | Feedback, logs, and live-mode cursor | runner only |

`inbox/` is the only directory where an acquisition process may place new
knowledge. Agents and integrations must call `fw.py ingest` (or the DSH
adapter) and must not write `drafts/`, `concepts/`, `history/`, or
`runtime/` directly.

## Publication rule

Every card is Markdown with an OKF frontmatter block. The runner normalizes,
scores, and validates it before writing. A card is published only when its
score meets the configured gate; weaker revisions remain in `drafts/` and the
previous verified version remains in `concepts/` with a snapshot in `history/`.

See [`schema/okf.v1.md`](schema/okf.v1.md) and
[`endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md`](../endlessWpKnowledgeRunner/docs/KNOWLEDGE-REPOSITORY.md).
