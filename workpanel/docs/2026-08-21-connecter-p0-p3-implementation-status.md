# Connecter P0-P3 implementation status

| Item | Value |
|---|---|
| Date | 2026-08-22 (updated) |
| Research object | `linlisWorkTeam/workpanelConnecter` |
| Source baseline | `main@e5b51eb9f89f9bcbb19480d58dc2de230d7e7591` |
| Working branch | `codex/connecter-p0-p3` (uncommitted at review time) |
| Full plan | `docs/superpowers/plans/2026-08-21-connecter-p0-p3-evolution.md` in the source repository |

## Implemented

- P0: twelve versioned migrations with checksums, pre-change backup and transaction rollback; Runner claim/ack/renew/fencing/result idempotency, pre-ack and running crash reclaim, dead letter and fenced operator requeue/cancel; stable Subject/Group identifiers and transport/application service boundaries.
- P1: Directory v2 Subject/Endpoint/Capability/Membership/Presence model; persisted and isolated v1/v2 Runner coexistence; one-time enrollment, approval, credential rotation/revocation and optional device-credential-only production mode; explainable local-first routing with explicit same-name ambiguity.
- P2: federation v1 envelope with TTL, hop, correlation, causation and trace; durable Host and Site inbox/outbox; delivery leases and conflict detection; directory exchange; A WorkPet command through Host to B Runner, durable `run.event` return to A, run projection and best-effort origin WorkPanel write-back.
- P3: separate message signing keys with active/next/revoked rotation and externally sourced secret support, direct mTLS client material, default-deny Site/Group/Subject/Operation/Direction/Capability/Data-classification ACL, audited runtime policy lifecycle and Host peer credential revoke/rotate, append-only redacted audit with controlled archive retention, structured logs, ops trace and corrected health metrics, accurate affected-delivery inventory, per-Site quotas and disk backpressure, compatibility matrix, backup/restore and operational runbooks.

## Verification evidence

All 49 local release gates pass in one fail-fast run, including device identity, TLS configuration, a real ephemeral-CA mutual TLS handshake/no-certificate rejection, policy matrix/API, quota, trace and short soak. Separate 600,000 ms and 480,000 ms repeated three-process federation soaks also passed (`FEDERATION_SOAK_OK`, wall times 602.4 s and 482.6 s). The E2E uses independent A Site, Host and B Site processes and databases on one machine. It verifies result projection through the original correlation ID and write-back to the origin WorkPanel. Host role routing now rejects WorkPet, WorkPanel and Runner execution APIs rather than merely leaving them unconfigured.

Dedicated recovery gates cover independent Site A, Site B, Host, Runner and WorkPanel restart/outage; lost Host ack response; target inbox retry while the Runner is unavailable; TTL expiry; and a late conflicting terminal. With Host down, Site A still reaches its local WorkPanel and Site B still completes a local Runner task. The target Site retains the message body after acknowledging Host, retries local dispatch without requiring Host to redeliver the body, and applies first-terminal-wins when callbacks arrive out of order.

A separate disaster-recovery gate deletes the temporary Host SQLite database after Host acceptance but before target delivery. The origin Site periodically reconciles non-terminal outbox entries, reconstructs the Host queue after restart, and completes the result round trip without duplicate execution.

## Conclusions

The code now implements the intended topology: WorkPet talks only to its Site Connecter; local traffic stays local; cross-site commands and results pass through the single durable Connecter Host; Runner execution remains on the target Site. The design has replaceable contracts and service boundaries rather than hard-coded direct server-to-server Agent calls.

## Recommendations

Before production promotion, run the 72-hour soak, deploy HTTPS/mTLS and production secret-store-backed signing keys, execute the test on at least two real Site servers plus a separate Host, connect metrics to alerting/on-call, and rehearse Host data loss and credential compromise with production-like backups and infrastructure.

## Evidence boundary

This is not a real multi-server or production TLS validation. The historical `127.0.0.1:8081` fixture was offline, but the current live WorkPanel canary at `127.0.0.1:8082` passed health, membership, no-@ admin routing and explicit @Agent dispatch (`E2_AT_MENTION_OK`) using configurable gate inputs. The 72-hour soak and real multi-server acceptance have not run. The implementation is therefore a locally verified release candidate, not confirmed production-ready software.
