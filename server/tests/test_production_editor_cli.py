from server.production_editor import build_parser


def test_production_editor_cli_exposes_staged_commands() -> None:
    parser = build_parser()

    planned = parser.parse_args(
        [
            "plan",
            "D:/Downloads/0806.mp4",
            "storage/deliverables/0806-production-v4",
            "--primary-reference",
            "10",
            "--secondary-reference",
            "4",
            "--flow-operation-budget",
            "3",
        ]
    )
    assert planned.command == "plan"
    assert planned.flow_operation_budget == 3

    generated = parser.parse_args(
        [
            "generate",
            "storage/deliverables/0806-production-v4",
            "--approve-paid-ops",
            "5",
        ]
    )
    assert generated.command == "generate"
    assert generated.approve_paid_ops == 5

    assembled = parser.parse_args(
        ["assemble", "storage/deliverables/0806-production-v4"]
    )
    assert assembled.command == "assemble"

    approved = parser.parse_args(
        [
            "approve",
            "storage/deliverables/0806-production-v4",
            "--reviewer",
            "user",
        ]
    )
    assert approved.command == "approve"


def test_production_editor_cli_exposes_social_kinetic_reference_options() -> None:
    parser = build_parser()

    planned = parser.parse_args(
        [
            "plan",
            "D:/Downloads/0810.mp4",
            "storage/deliverables/0810-production-v2-human-reference",
            "--style-reference",
            "D:/Downloads/Profit Bricks_Reel 04.mp4",
            "--reference-profile",
            "social-kinetic",
            "--story-profile",
            "rofx-case",
            "--voice-policy",
            "reference-compressed",
            "--flow-operation-budget",
            "8",
        ]
    )
    assert planned.reference_profile == "social-kinetic"
    assert planned.story_profile == "rofx-case"
    assert planned.voice_policy == "reference-compressed"
    assert planned.flow_operation_budget == 8

    generated = parser.parse_args(
        [
            "generate",
            "storage/deliverables/0810-production-v2-human-reference",
            "--approve-paid-ops",
            "8",
        ]
    )
    assert generated.approve_paid_ops == 8
