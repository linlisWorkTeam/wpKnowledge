#!/usr/bin/env python3
"""Validate the P0-A specification set and its Draft 2020-12 contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import sys

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
    from referencing import Registry, Resource
except ImportError as exc:
    raise SystemExit(
        "Missing validation dependency. Run: python -m pip install jsonschema"
    ) from exc


SPEC_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = SPEC_ROOT / "schemas"


def load_schemas() -> dict[str, dict]:
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMA_ROOT.glob("*.schema.json"))
    }
    ids = [schema["$id"] for schema in schemas.values()]
    if len(ids) != len(set(ids)):
        raise AssertionError("Schema $id values must be unique")
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # check_schema raises a detailed SchemaError
            raise AssertionError(f"Invalid Draft 2020-12 schema: {name}") from exc
    return schemas


def build_registry(schemas: dict[str, dict]) -> Registry:
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
    )


def validator(name: str, schemas: dict[str, dict], registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(
        schemas[name], registry=registry, format_checker=FormatChecker()
    )


def expect_invalid(instance: dict, contract: Draft202012Validator, label: str) -> None:
    try:
        contract.validate(instance)
    except ValidationError:
        return
    raise AssertionError(f"Invalid fixture unexpectedly passed: {label}")


def artifact(seed: str = "a") -> dict:
    return {
        "artifactId": f"art_{seed * 8}",
        "mediaType": "application/json",
        "sha256": seed * 64,
        "size": 1,
    }


def command(agent_type: str, payload: dict) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "commandId": f"cmd-{agent_type}",
        "runId": "run-1",
        "agentType": agent_type,
        "generationKey": f"generation-{agent_type}-0001",
        "payload": payload,
    }


def result(agent_type: str, payload: dict, output_refs: list[dict] | None = None) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "commandId": f"cmd-{agent_type}",
        "runId": "run-1",
        "agentType": agent_type,
        "status": "SUCCEEDED",
        "outputRefs": output_refs or [],
        "payload": payload,
    }


def validate_agent_contracts(schemas: dict[str, dict], registry: Registry) -> tuple[int, int]:
    ref_a = artifact("a")
    ref_b = artifact("b")
    correction = {
        "correctionId": "COR-0001",
        "knowledgePath": "modules/example/behavior",
        "criterion": "AC-FLOW-002",
        "evidenceRefs": [ref_a],
        "risk": "Incorrect behavior remains published",
    }
    commands = [
        command("orchestrator", {"policyRef": ref_a, "moduleRefs": [ref_b]}),
        command("docgen", {"moduleId": "example", "sourceRefs": [ref_a], "publicInterfaceRefs": [ref_b]}),
        command("docworker", {"moduleId": "example", "sourceRefs": [ref_a], "publicInterfaceRefs": [ref_b]}),
        command("testgen", {"moduleId": "example", "sourceSnapshotRef": ref_a, "publicInterfaceRefs": [ref_b], "languageId": "cpp", "testPolicyRef": ref_a}),
        command("codegen", {"knowledgeRef": ref_a, "publicInterfaceRefs": [ref_b], "languageId": "cpp", "buildContractRef": ref_a}),
        command("check", {"diffRef": ref_a, "criteriaRef": ref_b, "publicInterfaceRefs": [ref_a]}),
        command("review", {"knowledgeRef": ref_a, "evaluationReportRef": ref_b, "criteriaRef": ref_a}),
    ]
    command_validator = validator("agent-command.schema.json", schemas, registry)
    for fixture in commands:
        command_validator.validate(fixture)
        invalid = deepcopy(fixture)
        invalid["payload"]["unexpected"] = True
        expect_invalid(invalid, command_validator, f"{fixture['agentType']} command extra field")

    plan_node = {
        "nodeId": "node-docgen-1",
        "agentType": "docgen",
        "dependsOn": [],
        "generationKey": "generation-node-0001",
        "inputSchema": "https://wpknowledge.local/schemas/agent-command/v1",
        "outputSchema": "https://wpknowledge.local/schemas/agent-result/v1",
        "resourceClaims": ["knowledge:example"],
        "artifactExpectations": ["knowledgeCandidate"],
    }
    results = [
        result("orchestrator", {"resultKind": "plan", "nodes": [plan_node]}),
        result("docgen", {"resultKind": "knowledgeCandidate", "bodyRef": ref_a, "provenance": [ref_b], "changedPaths": ["modules/example"]}, [ref_a]),
        result("docworker", {"resultKind": "knowledgeChunk", "chunkRef": ref_a, "provenance": [ref_b]}, [ref_a]),
        result("testgen", {"resultKind": "testCandidates", "candidateSetRef": ref_a, "caseManifestRef": ref_b, "oracleClaims": ["claim-1"]}, [ref_a, ref_b]),
        result("codegen", {"resultKind": "codeArtifact", "codeRef": ref_a}, [ref_a]),
        result("check", {"resultKind": "findings", "findings": []}),
        result("review", {"resultKind": "attribution", "corrections": [correction], "unresolvedRisks": []}, [ref_a]),
    ]
    failed_result = result("docgen", {"resultKind": "error", "errorCode": "AGENT_OUTPUT_INVALID", "message": "invalid output", "retryable": True})
    failed_result["status"] = "FAILED"
    results.append(failed_result)

    result_validator = validator("agent-result.schema.json", schemas, registry)
    for fixture in results:
        result_validator.validate(fixture)
        invalid = deepcopy(fixture)
        invalid["payload"]["unexpected"] = True
        expect_invalid(invalid, result_validator, f"{fixture['agentType']} result extra field")

    mismatched = deepcopy(results[0])
    mismatched["agentType"] = "codegen"
    expect_invalid(mismatched, result_validator, "result kind does not match agent type")
    return len(commands), len(results)


def validate_evaluation_report(schemas: dict[str, dict], registry: Registry) -> None:
    ref_a = artifact("a")
    ref_b = artifact("b")
    report = {
        "schemaVersion": "1.0.0",
        "reportId": "report-1",
        "runId": "run-1",
        "iteration": 1,
        "inputRefs": [ref_a],
        "policyVersion": "gate-policy-1",
        "toolchainFingerprint": "clang-18-linux-amd64",
        "pluginFingerprint": "cpp-plugin-1",
        "testSetVersion": "core-gate-1",
        "modelConfigSummary": {"provider": "internal", "model": "example", "parametersDigest": "c" * 64},
        "promptDigest": "d" * 64,
        "compile": "PASS",
        "criticalResults": [{"caseId": "critical-1", "status": "PASS", "evidenceRefs": [ref_b]}],
        "repetitions": [
            {"caseId": "critical-1", "attempt": attempt, "status": "PASS", "durationMs": 10, "evidenceRefs": [ref_b]}
            for attempt in range(1, 6)
        ],
        "testSummary": {"total": 5, "passed": 5, "failed": 0, "errors": 0},
        "stability": "STABLE",
        "findings": [],
        "scoreComponents": {"coreGatePassRate": 1.0, "mutation": "not_available"},
        "reasonCodes": [],
    }
    report_validator = validator("evaluation-report.schema.json", schemas, registry)
    report_validator.validate(report)
    missing_provenance = deepcopy(report)
    del missing_provenance["pluginFingerprint"]
    expect_invalid(missing_provenance, report_validator, "evaluation provenance is required")
    unconstrained_repeat = deepcopy(report)
    unconstrained_repeat["repetitions"][0]["unexpected"] = True
    expect_invalid(unconstrained_repeat, report_validator, "repetition fields are closed")


def validate_supporting_contracts(schemas: dict[str, dict], registry: Registry) -> None:
    ref_a = artifact("a")
    validator("artifact-ref.schema.json", schemas, registry).validate(ref_a)
    correction = {
        "correctionId": "COR-0001",
        "knowledgePath": "modules/example/behavior",
        "criterion": "AC-FLOW-002",
        "evidenceRefs": [ref_a],
        "risk": "Incorrect behavior remains published",
    }
    validator("correction.schema.json", schemas, registry).validate(correction)
    event = {
        "schemaVersion": "1.0.0",
        "eventId": "event-1",
        "eventType": "RunCreated",
        "runId": "run-1",
        "occurredAt": "2026-08-31T09:22:00Z",
        "causationId": "command-1",
        "payload": {},
    }
    event_validator = validator("event.schema.json", schemas, registry)
    event_validator.validate(event)
    missing_causation = deepcopy(event)
    del missing_causation["causationId"]
    expect_invalid(missing_causation, event_validator, "event causation is required")


def validate_markdown_and_traceability() -> int:
    markdown_files = sorted(SPEC_ROOT.rglob("*.md"))
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    blocker_pattern = re.compile(r"\b(?:TBD|TODO)\b|待定", re.IGNORECASE)
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if blocker_pattern.search(text):
            raise AssertionError(f"Blocking placeholder in {path.relative_to(SPEC_ROOT)}")
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                raise AssertionError(f"Broken link in {path.relative_to(SPEC_ROOT)}: {raw_target}")

    requirements = []
    requirement_pattern = re.compile(r"^\| ((?:SYS|NFR)-\d+) \| P0 \|", re.MULTILINE)
    for name in ("system-requirements.md", "non-functional-requirements.md"):
        requirements.extend(requirement_pattern.findall((SPEC_ROOT / "01-requirements" / name).read_text(encoding="utf-8")))
    trace_text = (SPEC_ROOT / "13-verification" / "traceability-matrix.md").read_text(encoding="utf-8")
    for requirement in requirements:
        count = len(re.findall(rf"^\| {re.escape(requirement)} \|", trace_text, re.MULTILINE))
        if count != 1:
            raise AssertionError(f"{requirement} must appear exactly once in traceability matrix; got {count}")
    return len(requirements)


def main() -> int:
    schemas = load_schemas()
    registry = build_registry(schemas)
    command_count, result_count = validate_agent_contracts(schemas, registry)
    validate_evaluation_report(schemas, registry)
    validate_supporting_contracts(schemas, registry)
    requirement_count = validate_markdown_and_traceability()
    print(
        "SPEC_VALIDATION_OK",
        f"schemas={len(schemas)}",
        f"commands={command_count}",
        f"results={result_count}",
        f"p0={requirement_count}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
