# DeepSeek Harness adapter

This adapter registers `wp_knowledge_*` tools against the authenticated Knowledge Flywheel HTTP API. It never launches Python or a shell, and it does not decide whether knowledge is verified.

Configuration:

```text
WP_KNOWLEDGE_URL=http://127.0.0.1:4174
WP_KNOWLEDGE_WRITE_TOKEN=<same token used by the runner>
```

Read tools work without a write token. `wp_knowledge_scan` can only inspect the server-configured acquisition roots. Candidate ingestion and feedback fail closed when the token is absent. DSH remains an adapter dependency; no DSH type enters `packages/domain` or `packages/application`.

The old timer-driven harvester was intentionally removed. Scheduling and recovery belong to the workflow layer, while this adapter only translates tool requests to versioned API calls.
