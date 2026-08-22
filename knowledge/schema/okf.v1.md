# OKF v1 Card Contract

The flywheel persists one concept per Markdown file. The frontmatter is the
machine-controlled part; the Markdown body is the explanation that agents and
people consume.

Required fields:

- `schema_version`: starts with `okf.v1`.
- `name`: the same slug as the filename, using lowercase letters, digits, `-`,
  or `_`.
- `sources`: one or more provenance entries for verified cards. Drafts may be
  incomplete, but they cannot pass the publication gate without provenance.
  Prefer a repository-relative path plus `lines`, `commit`, `url`, or `pinned`
  anchors.
- `status`: exactly `draft` or `verified`, matching the directory.
- `verified`: `false` for drafts and `true` for verified cards.
- `version`: positive integer. A new verified revision increments it.
- non-empty Markdown body.

The runner owns `score`, `confidence`, `score_breakdown`, timestamps, and
history snapshots. A caller supplies candidate content and provenance; it does
not choose publication status by writing a file.
