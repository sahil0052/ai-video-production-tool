from server.produce_reference_exact import build_parser


def test_exact_reference_cli_exposes_plan_assemble_and_run() -> None:
    parser = build_parser()

    planned = parser.parse_args(
        [
            "plan",
            r"D:\Downloads\0806.mp4",
            r"D:\Downloads\Trading_Reel 02(06-08-26).mp4",
            r"storage\deliverables\0806-production-v5-exact",
        ]
    )
    assert planned.command == "plan"

    assembled = parser.parse_args(
        [
            "assemble",
            r"storage\deliverables\0806-production-v5-exact",
        ]
    )
    assert assembled.command == "assemble"

    complete = parser.parse_args(
        [
            "run",
            r"D:\Downloads\0806.mp4",
            r"D:\Downloads\Trading_Reel 02(06-08-26).mp4",
            r"storage\deliverables\0806-production-v5-exact",
        ]
    )
    assert complete.command == "run"
