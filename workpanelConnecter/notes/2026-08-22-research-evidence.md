# WorkPanelConnecter research evidence

Date: 2026-08-22

## Source revisions

- WorkPanelConnecter: `b133877` (P0-P3), `12ebb66` (mTLS gate), `d73e5c6` (v0.2.2 Windows artifacts); v0.2.3 documentation-audit candidate follows.
- WorkPanel baseline before implementation: `e5b51eb9f89f9bcbb19480d58dc2de230d7e7591`.
- Clowder AI: `8fd4824cb7db9124a0d863ba1b085a59b865c722`, commit date `2026-08-21T08:29:45Z`.
- wpKnowledge baseline: `d5d7a29ac1c1885eb07f81f1c53ffb595c1e1108` plus pre-existing local research changes.

## Local evidence

- v0.2.2: `npm run test:release-local` -> `RELEASE_LOCAL_GATE_OK gates=50`; v0.2.3 adds `test:docs` and passed `RELEASE_LOCAL_GATE_OK gates=51` on 2026-08-22.
- `npm run test:mtls-handshake` -> `MTLS_HANDSHAKE_E2E_OK`; ephemeral CA signs server/client certificates, and the no-client-certificate request is rejected before the handler.
- `CONNECTER_CANARY_URL=http://127.0.0.1:8082`, group `seed-group-workpanel` / `LinlisWorkPanel`, `npm run test:e2-canary` -> `E2_AT_MENTION_OK`.
- `node scripts/federation-soak.js --duration-ms=600000` -> exit 0 / `FEDERATION_SOAK_OK`, wall 602.4 s.
- `node scripts/federation-soak.js --duration-ms=480000` -> exit 0 / `FEDERATION_SOAK_OK`, wall 482.6 s.
- Full JS syntax and staged diff checks passed. Ignored `config/relay.json` and `data/` were not committed.

## External source commands

- `gh api repos/zts212653/clowder-ai`
- `gh api repos/zts212653/clowder-ai/commits/main`
- `gh api repos/zts212653/clowder-ai/git/trees/main?recursive=1`
- `gh api repos/zts212653/clowder-ai/contents/<path> -H 'Accept: application/vnd.github.raw+json'`
- GitHub repository API for LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, A2A, Temporal, Dapr, Clowder and OpenClaw metadata.

## Network notes

- Initial `git fetch` calls were reset, then both WorkPanelConnecter and wpKnowledge fetched successfully.
- Two attempts to clone Clowder failed because `github.com:443` was temporarily unreachable. GitHub API reads succeeded, so reports use immutable commit links and explicitly avoid runtime claims.

## Unverified

- No Clowder build, tests, Redis runtime or UI was executed.
- No real Connecter↔Clowder request was sent.
- No real multi-server Connecter mTLS deployment or 72-hour soak was completed.
- Competitor performance, enterprise support and security were not benchmarked.
