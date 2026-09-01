from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from PIL import Image, ImageStat

from app.editor.v8_graphics import render_graphic


@pytest.fixture
def workspace_tmp() -> Path:
    parent = (Path(__file__).parent / ".tmp_v8_graphics").resolve()
    root = parent / uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        resolved = root.resolve()
        if resolved.is_relative_to(parent):
            shutil.rmtree(resolved, ignore_errors=True)


@pytest.mark.parametrize(
    "asset_id",
    [
        "graphic-backtest-practice",
        "graphic-historical-data",
        "graphic-fixed-spread",
        "graphic-unit-price",
        "graphic-different-total",
        "graphic-entry-lot-risk",
    ],
)
def test_reference_counterweight_graphics_are_bright(
    workspace_tmp: Path,
    asset_id: str,
) -> None:
    output = workspace_tmp / f"{asset_id}.png"

    render_graphic(asset_id, output)

    with Image.open(output) as image:
        mean = ImageStat.Stat(image.convert("L")).mean[0]
    assert mean >= 205


def test_backtest_risk_graphic_remains_dark(
    workspace_tmp: Path,
) -> None:
    output = workspace_tmp / "risk.png"

    render_graphic("graphic-overfit-unseen", output)

    with Image.open(output) as image:
        mean = ImageStat.Stat(image.convert("L")).mean[0]
    assert mean <= 65


def test_bright_rule_uses_light_document_cards(
    workspace_tmp: Path,
) -> None:
    output = workspace_tmp / "entry-lot-risk.png"

    render_graphic("graphic-entry-lot-risk", output)

    with Image.open(output) as image:
        mean = ImageStat.Stat(image.convert("L")).mean[0]
    assert mean >= 220
