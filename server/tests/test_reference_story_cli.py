import importlib


def test_reference_story_cli_supports_plan_run_assemble_and_remaster():
    build_parser = importlib.import_module(
        "server.produce_reference_story"
    ).build_parser
    parser = build_parser()

    planned = parser.parse_args(
        [
            "plan",
            r"D:\Downloads\0809.mp4",
            r"storage\deliverables\0809-production-v1-reference-style",
        ]
    )
    run = parser.parse_args(
        [
            "run",
            r"D:\Downloads\0809.mp4",
            r"storage\deliverables\0809-production-v1-reference-style",
        ]
    )
    assembled = parser.parse_args(
        [
            "assemble",
            r"storage\deliverables\0809-production-v1-reference-style",
        ]
    )
    remastered = parser.parse_args(
        [
            "remaster",
            r"storage\deliverables\0809-production-v1-reference-style",
        ]
    )

    assert planned.command == "plan"
    assert run.command == "run"
    assert assembled.command == "assemble"
    assert remastered.command == "remaster"
