from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Iterable, Sequence

from app.editor.training_reference_profiles import profile_for_story


_SENTENCE_END = re.compile(r"[.!?।]$")
_PROTECTED_TERMS = {
    "ppi": {
        "ppi",
        "cpi",
        "bls",
        "goods",
        "services",
        "forecast",
        "actual",
        "spread",
    },
    "backtest": {
        "backtest",
        "strategy",
        "tester",
        "spread",
        "slippage",
        "execution",
        "forward",
        "demo",
    },
    "lot-size": {
        "lot",
        "size",
        "risk",
        "stop",
        "loss",
        "maximum",
        "fixed",
        "entry",
    },
}


@dataclass(frozen=True)
class PlannedCaptionToken:
    text: str
    start_ms: int
    end_ms: int
    highlighted: bool = False
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "highlighted": self.highlighted,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class PlannedCaptionPage:
    start_ms: int
    end_ms: int
    tokens: tuple[PlannedCaptionToken, ...]
    family: str
    anchor: str
    transition: str
    max_width: int
    font_size: int
    timeline_duration_ms: int

    @property
    def text(self) -> str:
        return " ".join(token.text for token in self.tokens)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "tokens": [token.to_dict() for token in self.tokens],
            "family": self.family,
            "anchor": self.anchor,
            "transition": self.transition,
            "max_width": self.max_width,
            "font_size": self.font_size,
        }


def _time_ms(word: dict[str, Any], key: str) -> int:
    if f"{key}_ms" in word:
        return round(float(word[f"{key}_ms"]))
    if key in word:
        return round(float(word[key]) * 1000)
    raise ValueError(f"Caption word is missing {key} timing")


def _text(word: dict[str, Any]) -> str:
    value = word.get("text", word.get("punctuated_word", word.get("word")))
    if value is None:
        raise ValueError("Caption word is missing text")
    return str(value).strip()


def _normalize_words(
    words: Sequence[dict[str, Any]],
) -> list[PlannedCaptionToken]:
    normalized = [
        PlannedCaptionToken(
            text=_text(word),
            start_ms=_time_ms(word, "start"),
            end_ms=_time_ms(word, "end"),
            confidence=(
                float(word["confidence"])
                if word.get("confidence") is not None
                else None
            ),
        )
        for word in words
        if _text(word)
    ]
    if any(token.end_ms <= token.start_ms for token in normalized):
        raise ValueError("Caption words require positive duration")
    if any(
        right.start_ms < left.start_ms
        for left, right in zip(normalized, normalized[1:])
    ):
        raise ValueError("Caption words must be ordered")
    return normalized


def _groups(
    words: Sequence[PlannedCaptionToken],
) -> list[tuple[PlannedCaptionToken, ...]]:
    groups: list[tuple[PlannedCaptionToken, ...]] = []
    cursor = 0
    while cursor < len(words):
        remaining = len(words) - cursor
        take = 2 if remaining == 4 else min(3, remaining)
        for offset in range(take):
            token = words[cursor + offset]
            if _SENTENCE_END.search(token.text):
                take = offset + 1
                break
            if offset > 0:
                span = token.end_ms - words[cursor].start_ms
                gap = token.start_ms - words[cursor + offset - 1].end_ms
                if span > 1_300 or gap > 360:
                    take = offset
                    break
        take = max(1, take)
        groups.append(tuple(words[cursor : cursor + take]))
        cursor += take
    return groups


def _role_at(
    role_spans: Sequence[dict[str, Any]],
    at_ms: int,
) -> str:
    for span in role_spans:
        if int(span["start_ms"]) <= at_ms < int(span["end_ms"]):
            return str(span["role"])
    return "explanation"


def _style_for(story_id: str, role: str) -> tuple[str, str, str, int, int]:
    if role in {"presenter-cta", "cta"}:
        return ("compact-pill", "center-76", "hard-cut", 500, 38)
    if story_id == "ppi" and role in {
        "evidence",
        "evidence-overview",
        "evidence-excerpt",
        "direct-evidence",
    }:
        return (
            "documentary-clean",
            "center-71",
            "hard-cut",
            620,
            36,
        )
    if story_id == "lot-size" and role in {
        "product-action",
        "product-macro",
        "demonstration",
    }:
        return ("outlined-demo", "center-69", "hard-cut", 760, 58)
    return ("technical-mono", "center-74", "hard-cut", 500, 33)


def _page_priority(story_id: str, page: PlannedCaptionPage) -> int:
    lowered = {
        re.sub(r"[^a-z0-9-]", "", token.text.casefold())
        for token in page.tokens
    }
    score = sum(len(token.text) >= 6 for token in page.tokens)
    if lowered & _PROTECTED_TERMS[story_id]:
        score += 20
    if any(any(character.isdigit() for character in text) for text in lowered):
        score += 20
    if page.family in {"documentary-clean", "outlined-demo", "compact-pill"}:
        score += 10
    return score


def covered_ms(pages: Iterable[PlannedCaptionPage]) -> int:
    ranges = sorted((page.start_ms, page.end_ms) for page in pages)
    if not ranges:
        return 0
    total = 0
    current_start, current_end = ranges[0]
    for start, end in ranges[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def duration_ms(pages: Sequence[PlannedCaptionPage]) -> int:
    return pages[0].timeline_duration_ms if pages else 0


def _reduce_coverage(
    *,
    story_id: str,
    pages: list[PlannedCaptionPage],
    minimum_ms: int,
    maximum_ms: int,
) -> list[PlannedCaptionPage]:
    selected = pages[:]
    while covered_ms(selected) > maximum_ms and len(selected) > 1:
        candidates = sorted(
            range(len(selected)),
            key=lambda index: (
                _page_priority(story_id, selected[index]),
                index in {0, len(selected) - 1},
                selected[index].end_ms - selected[index].start_ms,
            ),
        )
        removed = False
        for index in candidates:
            proposed = selected[:index] + selected[index + 1 :]
            if covered_ms(proposed) >= minimum_ms:
                selected = proposed
                removed = True
                break
        if not removed:
            break
    return selected


def _expand_coverage(
    pages: list[PlannedCaptionPage],
    target_ms: int,
) -> list[PlannedCaptionPage]:
    expanded = pages[:]
    for index, page in enumerate(expanded):
        if covered_ms(expanded) >= target_ms:
            break
        next_start = (
            expanded[index + 1].start_ms
            if index + 1 < len(expanded)
            else page.timeline_duration_ms
        )
        available = min(
            next_start - page.end_ms,
            1_300 - (page.end_ms - page.start_ms),
            target_ms - covered_ms(expanded),
        )
        if available > 0:
            expanded[index] = replace(page, end_ms=page.end_ms + available)
    return expanded


def plan_captions(
    story_id: str,
    *,
    words: Sequence[dict[str, Any]],
    duration_ms: int,
    role_spans: Sequence[dict[str, Any]] | None = None,
) -> list[PlannedCaptionPage]:
    profile = profile_for_story(story_id)
    tokens = _normalize_words(words)
    if not tokens:
        return []
    spans = role_spans or []
    pages: list[PlannedCaptionPage] = []
    previous_end = 0
    for group in _groups(tokens):
        start = max(previous_end, group[0].start_ms)
        natural_end = min(duration_ms, group[-1].end_ms)
        end = min(
            duration_ms,
            max(natural_end, start + 350),
            start + 1_300,
        )
        if end <= start:
            continue
        midpoint = start + (end - start) // 2
        family, anchor, transition, max_width, font_size = _style_for(
            profile.story_id,
            _role_at(spans, midpoint),
        )
        pages.append(
            PlannedCaptionPage(
                start_ms=start,
                end_ms=end,
                tokens=group,
                family=family,
                anchor=anchor,
                transition=transition,
                max_width=max_width,
                font_size=font_size,
                timeline_duration_ms=duration_ms,
            )
        )
        previous_end = end

    minimum_ms = round(duration_ms * profile.caption_coverage[0])
    maximum_ms = round(duration_ms * profile.caption_coverage[1])
    pages = _reduce_coverage(
        story_id=profile.story_id,
        pages=pages,
        minimum_ms=minimum_ms,
        maximum_ms=maximum_ms,
    )
    if covered_ms(pages) < minimum_ms:
        pages = _expand_coverage(
            pages,
            target_ms=round(
                duration_ms
                * sum(profile.caption_coverage)
                / 2
            ),
        )
    if profile.story_id == "backtest":
        pages = [
            (
                replace(
                    page,
                    family="technical-mono",
                    anchor="center-74",
                    transition="hard-cut",
                    max_width=500,
                    font_size=33,
                )
                if page.family != "technical-mono"
                else page
            )
            for page in pages
        ]
    return pages
