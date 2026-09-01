from server.process_video import build_parser
from server.produce_reference_edit import (
    build_parser as build_reference_parser,
)


def test_cli_defaults_to_training_derived_profile_and_auto_assets() -> None:
    arguments = build_parser().parse_args(["raw.mp4", "edited.mp4"])

    assert arguments.profile == "tech-story-v1"
    assert arguments.assets == "auto"
    assert arguments.internet_assets == "auto"


def test_reference_production_cli_exposes_locked_contract() -> None:
    arguments = build_reference_parser().parse_args(
        [
            "raw.mp4",
            "deliverable",
            "--primary-reference",
            "10",
            "--secondary-reference",
            "4",
            "--asset-policy",
            "maximum-match",
            "--time-budget-min",
            "30",
        ]
    )

    assert arguments.primary_reference == 10
    assert arguments.secondary_reference == 4
    assert arguments.asset_policy == "maximum-match"
    assert arguments.time_budget_min == 30


def test_reference_production_cli_exposes_reference_max_rebuild_contract() -> None:
    arguments = build_reference_parser().parse_args(
        [
            r"D:\Downloads\0806.mp4",
            r"storage\deliverables\0806-production-v2",
            "--primary-reference",
            "10",
            "--secondary-reference",
            "4",
            "--quality-target",
            "reference-max",
            "--capture-profile",
            "local-metatrader",
            "--voice-policy",
            "preserve-verbatim",
            "--asset-policy",
            "free-licensed",
            "--visual-revision",
            "v3",
        ]
    )

    assert arguments.quality_target == "reference-max"
    assert arguments.capture_profile == "local-metatrader"
    assert arguments.voice_policy == "preserve-verbatim"
    assert arguments.asset_policy == "free-licensed"
    assert arguments.visual_revision == "v3"


def test_reference_production_defaults_to_the_non_rejected_visual_revision() -> None:
    arguments = build_reference_parser().parse_args(
        [
            "raw.mp4",
            "deliverable",
            "--primary-reference",
            "10",
            "--secondary-reference",
            "4",
        ]
    )

    assert arguments.visual_revision == "v4"
