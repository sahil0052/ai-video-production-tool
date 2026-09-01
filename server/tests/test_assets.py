from pathlib import Path

from app.editor.assets import discover_local_assets


def test_discover_local_assets_matches_keywords_and_records_license(
    tmp_path: Path,
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    clip = library / "ai-chip-closeup.mp4"
    clip.write_bytes(b"video")
    clip.with_suffix(".license.txt").write_text(
        "Licensed internal library",
        encoding="utf-8",
    )
    (library / "robot-hand.jpg").write_bytes(b"image")

    assets = discover_local_assets(
        library,
        text="This new AI chip runs much faster",
        start_ms=1200,
        end_ms=2600,
        limit=2,
    )

    assert len(assets) == 1
    assert assets[0].kind == "video"
    assert assets[0].path == str(clip.resolve())
    assert assets[0].provenance == "local-library"
    assert assets[0].license == "Licensed internal library"
    assert assets[0].start_ms == 1200
    assert assets[0].end_ms == 2600


def test_discover_local_assets_returns_empty_for_unrelated_media(
    tmp_path: Path,
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "cooking-pasta.jpg").write_bytes(b"image")

    assert (
        discover_local_assets(
            library,
            text="CPU compiler performance",
            start_ms=0,
            end_ms=1000,
        )
        == []
    )
