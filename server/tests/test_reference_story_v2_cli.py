from __future__ import annotations

import importlib
import json
import sys


def test_v2_cli_supports_plan_generate_accept_assemble_and_remaster():
    parser = importlib.import_module(
        "server.produce_reference_story_v2"
    ).build_parser()

    planned = parser.parse_args(["plan", "raw.mp4", "out"])
    generated = parser.parse_args(
        ["generate", "out", "--approve-paid-ops", "5"]
    )
    accepted = parser.parse_args(
        [
            "accept",
            "out",
            "--shot-id",
            "flow-update-module",
            "--attempt",
            "1",
            "--start-ms",
            "400",
            "--end-ms",
            "2200",
        ]
    )
    assembled = parser.parse_args(["assemble", "out"])
    remastered = parser.parse_args(["remaster", "out"])

    assert planned.command == "plan"
    assert generated.command == "generate"
    assert generated.approve_paid_ops == 5
    assert accepted.command == "accept"
    assert accepted.end_ms - accepted.start_ms == 1800
    assert assembled.command == "assemble"
    assert remastered.command == "remaster"


def test_v2_cli_main_routes_plan_and_prints_json(monkeypatch, capsys):
    module = importlib.import_module("server.produce_reference_story_v2")
    calls = []

    def fake_plan(*, source, output_dir):
        calls.append((source, output_dir))
        return {"state": "awaiting-generation-approval"}

    monkeypatch.setattr(
        module,
        "build_reference_story_v2_blueprint",
        fake_plan,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["produce_reference_story_v2.py", "plan", "raw.mp4", "out"],
    )

    assert module.main() == 0
    assert [(str(source), str(output)) for source, output in calls] == [
        ("raw.mp4", "out")
    ]
    assert json.loads(capsys.readouterr().out) == {
        "state": "awaiting-generation-approval"
    }


def test_v2_cli_main_maps_acceptance_scores(monkeypatch):
    module = importlib.import_module("server.produce_reference_story_v2")
    captured = {}

    def fake_accept(**kwargs):
        captured.update(kwargs)
        return {"accepted": True}

    monkeypatch.setattr(
        module,
        "review_flow_candidate",
        fake_accept,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "produce_reference_story_v2.py",
            "accept",
            "out",
            "--shot-id",
            "flow-update-module",
            "--attempt",
            "1",
            "--start-ms",
            "400",
            "--end-ms",
            "2200",
            "--semantic-score",
            "5",
            "--composition-score",
            "4",
            "--motion-score",
            "4",
            "--continuity-score",
            "4",
            "--style-score",
            "4",
            "--editability-score",
            "4",
        ],
    )

    assert module.main() == 0
    assert captured["accepted"] is True
    assert captured["reviewer"] == "codex-production-review"
    assert captured["scores"] == {
        "prompt_fidelity": 5,
        "composition": 4,
        "motion_quality": 4,
        "continuity": 4,
        "artifact_integrity": 4,
        "editorial_usefulness": 4,
    }
