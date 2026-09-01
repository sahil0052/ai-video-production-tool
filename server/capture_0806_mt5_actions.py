from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Callable

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import ImageGrab


USER32 = ctypes.windll.user32
USER32.SetProcessDPIAware()

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
SW_MAXIMIZE = 3

VK_ALT = 0x12
VK_CONTROL = 0x11
VK_DOWN = 0x28
VK_END = 0x23
VK_ENTER = 0x0D
VK_ESCAPE = 0x1B
VK_HOME = 0x24
VK_M = 0x4D
VK_OEM_PERIOD = 0xBE
VK_R = 0x52
VK_SHIFT = 0x10
VK_V = 0x56
WM_CLOSE = 0x0010


class Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


@dataclass(frozen=True)
class WindowTarget:
    hwnd: int
    title: str
    client_left: int
    client_top: int
    client_width: int
    client_height: int


def _window_text(hwnd: int) -> str:
    length = USER32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    USER32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def _find_window(
    *,
    required_title_parts: tuple[str, ...],
) -> WindowTarget:
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        wintypes.HWND,
        wintypes.LPARAM,
    )
    def callback(hwnd: int, _: int) -> bool:
        if not USER32.IsWindowVisible(hwnd):
            return True
        title = _window_text(hwnd)
        if all(part.casefold() in title.casefold() for part in required_title_parts):
            matches.append(hwnd)
        return True

    USER32.EnumWindows(callback, 0)
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one safe capture window for "
            f"{required_title_parts!r}; found {len(matches)}."
        )
    hwnd = matches[0]
    USER32.ShowWindow(hwnd, SW_MAXIMIZE)
    _activate(hwnd)
    time.sleep(0.5)
    rect = Rect()
    origin = Point()
    if not USER32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("Unable to read capture-window client geometry.")
    if not USER32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError("Unable to resolve capture-window screen origin.")
    return WindowTarget(
        hwnd=hwnd,
        title=_window_text(hwnd),
        client_left=origin.x,
        client_top=origin.y,
        client_width=rect.right,
        client_height=rect.bottom,
    )


def _activate(hwnd: int) -> None:
    _tap(VK_ALT)
    USER32.SetForegroundWindow(hwnd)
    USER32.SwitchToThisWindow(hwnd, True)
    time.sleep(0.15)


def _key_down(key: int) -> None:
    USER32.keybd_event(key, 0, 0, 0)


def _key_up(key: int) -> None:
    USER32.keybd_event(key, 0, KEYEVENTF_KEYUP, 0)


def _tap(key: int, *, delay: float = 0.08) -> None:
    _key_down(key)
    _key_up(key)
    time.sleep(delay)


def _combo(*keys: int) -> None:
    for key in keys[:-1]:
        _key_down(key)
    _tap(keys[-1])
    for key in reversed(keys[:-1]):
        _key_up(key)
    time.sleep(0.12)


def _move(x: int, y: int, *, duration: float = 0.28) -> None:
    current = Point()
    USER32.GetCursorPos(ctypes.byref(current))
    steps = max(2, round(duration * 60))
    for index in range(1, steps + 1):
        progress = index / steps
        USER32.SetCursorPos(
            round(current.x + (x - current.x) * progress),
            round(current.y + (y - current.y) * progress),
        )
        time.sleep(duration / steps)


def _left_click(x: int, y: int, *, count: int = 1) -> None:
    _move(x, y)
    for _ in range(count):
        USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.13)


def _right_click(x: int, y: int) -> None:
    _move(x, y)
    USER32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    USER32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    time.sleep(0.2)


def _drag(
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    duration: float = 0.55,
) -> None:
    _move(*start)
    USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    current = Point(*start)
    steps = max(2, round(duration * 60))
    for index in range(1, steps + 1):
        progress = index / steps
        USER32.SetCursorPos(
            round(current.x + (end[0] - current.x) * progress),
            round(current.y + (end[1] - current.y) * progress),
        )
        time.sleep(duration / steps)
    USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.12)


def _wheel(clicks: int) -> None:
    USER32.mouse_event(
        MOUSEEVENTF_WHEEL,
        0,
        0,
        clicks * 120,
        0,
    )
    time.sleep(0.3)


def _owned_window(
    owner_hwnd: int,
    *,
    required_title_part: str | None = None,
) -> int | None:
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        wintypes.HWND,
        wintypes.LPARAM,
    )
    def callback(hwnd: int, _: int) -> bool:
        if (
            USER32.IsWindowVisible(hwnd)
            and USER32.GetWindow(hwnd, 4) == owner_hwnd
        ):
            title = _window_text(hwnd)
            if (
                required_title_part is None
                or required_title_part.casefold() in title.casefold()
            ):
                matches.append(hwnd)
        return True

    USER32.EnumWindows(callback, 0)
    return matches[0] if matches else None


def _dismiss_owned_window(
    owner_hwnd: int,
    *,
    required_title_part: str | None = None,
) -> None:
    child = _owned_window(
        owner_hwnd,
        required_title_part=required_title_part,
    )
    if child is None:
        return
    USER32.SendMessageW(child, WM_CLOSE, 0, 0)
    time.sleep(0.5)


def _assert_algo_trading_off(target: WindowTarget) -> None:
    screenshot = ImageGrab.grab(
        bbox=(
            target.client_left + 390,
            target.client_top,
            target.client_left + 455,
            target.client_top + 42,
        ),
        all_screens=True,
    ).convert("RGB")
    red_pixels = sum(
        1
        for red, green, blue in screenshot.getdata()
        if red >= 120 and green <= 95 and blue <= 95
    )
    if red_pixels < 8:
        raise RuntimeError(
            "Algo Trading does not appear safely disabled; capture aborted."
        )


def _record(
    *,
    target: WindowTarget,
    output: Path,
    duration_seconds: float,
    action: Callable[[], None],
) -> None:
    if target.client_width != 1920 or target.client_height > 1080:
        raise RuntimeError(
            "Unexpected capture geometry: "
            f"{target.client_width}x{target.client_height}."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    pad_top = (1080 - target.client_height) // 2
    command = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "gdigrab",
        "-draw_mouse",
        "1",
        "-framerate",
        "60",
        "-offset_x",
        str(target.client_left),
        "-offset_y",
        str(target.client_top),
        "-video_size",
        f"{target.client_width}x{target.client_height}",
        "-t",
        f"{duration_seconds:.3f}",
        "-i",
        "desktop",
        "-vf",
        (
            f"pad=1920:1080:0:{pad_top}:color=0x111111,"
            "fps=60"
        ),
        "-an",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-tune",
        "hq",
        "-cq",
        "18",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    _activate(target.hwnd)
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        shell=False,
    )
    time.sleep(0.65)
    action()
    _, stderr = process.communicate(timeout=duration_seconds + 8)
    if process.returncode:
        raise RuntimeError(
            f"Capture failed for {output.name}: "
            f"{stderr.decode(errors='replace')}"
        )
    if output.stat().st_size < 50_000:
        raise RuntimeError(f"Capture is unexpectedly small: {output}")


def _metaeditor_compile_action() -> None:
    _move(650, 74)
    _left_click(650, 74)
    time.sleep(0.9)
    _drag((408, 300), (790, 300))
    time.sleep(0.7)


def _metaeditor_rule_action() -> None:
    _left_click(720, 430)
    _combo(VK_CONTROL, VK_HOME)
    time.sleep(0.35)
    _drag((440, 438), (960, 438))
    time.sleep(0.7)
    _drag((408, 300), (790, 300))
    time.sleep(0.6)


def _navigator_action() -> None:
    _left_click(22, 230)
    time.sleep(0.65)
    _left_click(22, 230)
    time.sleep(0.55)
    _left_click(122, 302)
    time.sleep(0.8)


def _open_ea_inputs(target: WindowTarget) -> None:
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )
    _activate(target.hwnd)
    _left_click(700, 160)
    _left_click(122, 302, count=2)
    time.sleep(0.85)


def _hook_action(target: WindowTarget) -> None:
    _open_ea_inputs(target)
    _left_click(930, 510)
    time.sleep(0.65)
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )


def _risk_input_action(target: WindowTarget) -> None:
    _open_ea_inputs(target)
    _left_click(930, 510, count=2)
    _combo(VK_CONTROL, ord("A"))
    for key in (ord("1"), VK_OEM_PERIOD, ord("5")):
        _tap(key)
    time.sleep(0.65)
    _left_click(930, 535)
    time.sleep(0.6)
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )


def _risk_alternate_action(target: WindowTarget) -> None:
    _open_ea_inputs(target)
    _left_click(930, 535)
    time.sleep(0.55)
    _left_click(930, 560)
    time.sleep(0.7)
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )


def _attach_action(target: WindowTarget) -> None:
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )
    _activate(target.hwnd)
    _right_click(122, 302)
    time.sleep(0.45)
    _left_click(185, 327)
    time.sleep(0.85)
    _left_click(930, 510)
    time.sleep(0.65)
    _dismiss_owned_window(
        target.hwnd,
        required_title_part="ReferenceSafeEA",
    )


def _toggle_strategy_tester(target: WindowTarget) -> None:
    _activate(target.hwnd)
    _combo(VK_CONTROL, VK_R)
    time.sleep(0.8)


def _strategy_action() -> None:
    _left_click(935, 881)
    _tap(VK_END)
    _tap(VK_ENTER)
    time.sleep(0.55)
    _left_click(230, 975)
    time.sleep(0.55)
    _left_click(160, 975)
    time.sleep(0.55)
    _left_click(75, 975)
    time.sleep(0.55)


def capture_all(output_dir: Path) -> list[Path]:
    metaeditor = _find_window(required_title_parts=("MetaEditor",))
    terminal = _find_window(
        required_title_parts=("MetaQuotes-Demo", "Read Only"),
    )
    _assert_algo_trading_off(terminal)

    outputs: list[Path] = []
    specifications: list[
        tuple[WindowTarget, str, float, Callable[[], None]]
    ] = [
        (
            metaeditor,
            "metaeditor-compile-action-v2.mp4",
            5.2,
            _metaeditor_compile_action,
        ),
        (
            metaeditor,
            "metaeditor-rule-highlight-v2.mp4",
            5.2,
            _metaeditor_rule_action,
        ),
        (
            terminal,
            "mt5-navigator-action-v2.mp4",
            5.2,
            _navigator_action,
        ),
        (
            terminal,
            "mt5-hook-action-v2.mp4",
            5.2,
            lambda: _hook_action(terminal),
        ),
        (
            terminal,
            "mt5-risk-input-action-v2.mp4",
            5.8,
            lambda: _risk_input_action(terminal),
        ),
        (
            terminal,
            "mt5-risk-alternate-action-v2.mp4",
            5.5,
            lambda: _risk_alternate_action(terminal),
        ),
        (
            terminal,
            "mt5-attach-action-v2.mp4",
            5.5,
            lambda: _attach_action(terminal),
        ),
    ]
    for target, filename, duration, action in specifications:
        output = output_dir / filename
        _record(
            target=target,
            output=output,
            duration_seconds=duration,
            action=action,
        )
        outputs.append(output)

    _activate(terminal.hwnd)
    _toggle_strategy_tester(terminal)
    _left_click(95, 926)
    time.sleep(0.8)
    _drag((1_000, 859), (1_000, 655), duration=0.5)
    strategy_output = output_dir / "mt5-strategy-tester-action-v2.mp4"
    _record(
        target=terminal,
        output=strategy_output,
        duration_seconds=5.2,
        action=_strategy_action,
    )
    outputs.append(strategy_output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture credential-free, action-based MT5 footage for the "
            "0806 reference-parity edit."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parent.parent
            / "storage"
            / "assets"
            / "product"
            / "0806-v8-captures"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = capture_all(args.output_dir.resolve())
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
