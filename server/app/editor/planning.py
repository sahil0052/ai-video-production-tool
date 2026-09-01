from __future__ import annotations

import re

from app.models import (
    AudioPlan,
    CaptionFamily,
    CaptionPage,
    CaptionToken,
    EditorialVisual,
    EditPlanV1,
    GraphicCue,
    OutputSpec,
    QCTargets,
    ScenePlan,
    SceneRole,
    StyleVariant,
    TimelineMapSegment,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)

_STYLE_SIGNALS: dict[StyleVariant, set[str]] = {
    "tech-news": {
        "announced",
        "breaking",
        "news",
        "released",
        "report",
        "tweet",
        "update",
    },
    "cinematic-concept": {
        "future",
        "imagine",
        "world",
        "concept",
        "vision",
        "cinematic",
        "replace",
    },
    "technical-explanation": {
        "algorithm",
        "api",
        "chip",
        "code",
        "compiler",
        "cpu",
        "data",
        "engineer",
        "forex",
        "model",
        "network",
        "risk",
        "rules",
        "security",
        "strategy",
        "trading",
    },
    "product-demo": {
        "app",
        "camera",
        "demo",
        "feature",
        "phone",
        "screen",
        "test",
        "tool",
        "watch",
    },
    "hardware-launch": {
        "device",
        "hand",
        "hardware",
        "humanoid",
        "robot",
        "sensor",
        "wearable",
    },
    "hyper-montage": {
        "crazy",
        "everything",
        "fast",
        "insane",
        "massive",
        "million",
        "viral",
    },
}

_FILLER_WORDS = {"ah", "erm", "hmm", "uh", "um"}

_CAPTION_DEFAULTS: dict[
    CaptionFamily,
    tuple[str, str, int],
] = {
    "technical-mono": ("center-74", "hard-cut", 900),
    "documentary-clean": ("center-71", "hard-cut", 920),
    "compact-pill": ("center-76", "fade-up", 900),
    "outlined-demo": ("center-74", "scale-in", 940),
    "display-emphasis": ("upper-62", "scale-in", 940),
}

_TERMINAL_PUNCTUATION = re.compile(r"[.!?][\"')\]]*$")
_CLAUSE_PUNCTUATION = re.compile(r"[,;:][\"')\]]*$")
_CURRENCY_TOKEN = re.compile(r"^[€£₹$]\s?\d[\d,._-]*[.!?]?$")


def snap_to_beat_ms(time_ms: int, *, bpm: int = 120) -> int:
    beat_ms = 60_000 / bpm
    return round(int(time_ms / beat_ms + 0.5) * beat_ms)


def classify_sentence(
    text: str,
    *,
    index: int,
    total: int,
) -> SceneRole:
    normalized = text.lower()
    if index == 0:
        return "hook"
    if index == total - 1 and any(
        signal in normalized
        for signal in {"comment", "follow", "try", "use it", "now"}
    ):
        return "cta"
    if any(
        signal in normalized
        for signal in {"benchmark", "data", "evidence", "proves", "report"}
    ):
        return "evidence"
    if any(
        signal in normalized
        for signal in {"but", "however", "instead", "unlike", "versus"}
    ):
        return "contrast"
    if any(
        signal in normalized
        for signal in {"click", "demo", "open", "screen", "show", "watch"}
    ):
        return "demonstration"
    if any(
        signal in normalized
        for signal in {"because", "how", "means", "why"}
    ):
        return "explanation"
    if index == total - 1:
        return "payoff"
    return "claim"


def choose_style_variant(text: str) -> StyleVariant:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    scores = {
        variant: len(tokens.intersection(signals))
        for variant, signals in _STYLE_SIGNALS.items()
    }
    priority: list[StyleVariant] = [
        "hardware-launch",
        "product-demo",
        "technical-explanation",
        "tech-news",
        "hyper-montage",
        "cinematic-concept",
    ]
    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return "tech-news"
    return next(variant for variant in priority if scores[variant] == best_score)


def _qc_targets_for_variant(style_variant: StyleVariant) -> QCTargets:
    pacing = {
        "tech-news": (28, 55, 900, 1900),
        "cinematic-concept": (24, 45, 1200, 2400),
        "technical-explanation": (15, 50, 1000, 2600),
        "product-demo": (15, 45, 1000, 3400),
        "hardware-launch": (25, 50, 1000, 2100),
        "hyper-montage": (40, 75, 700, 1400),
    }[style_variant]
    return QCTargets(
        min_cuts_per_minute=pacing[0],
        max_cuts_per_minute=pacing[1],
        min_median_shot_ms=pacing[2],
        max_median_shot_ms=pacing[3],
    )


def build_timeline_map(
    segments: list[TranscriptSegment],
    *,
    source_duration_ms: int,
    max_pause_ms: int = 120,
    kept_pause_ms: int = 60,
    edge_padding_ms: int = 80,
) -> list[TimelineMapSegment]:
    words = _flatten_words(segments)
    if not words:
        return [
            TimelineMapSegment(
                source_start_ms=0,
                source_end_ms=source_duration_ms,
                output_start_ms=0,
                output_end_ms=source_duration_ms,
            )
        ]

    ranges: list[tuple[int, int]] = []
    current_start = max(0, _to_ms(words[0].start) - edge_padding_ms)
    previous_end = _to_ms(words[0].end)
    half_pause = kept_pause_ms // 2

    for word in words[1:]:
        next_start = _to_ms(word.start)
        if next_start - previous_end > max_pause_ms:
            ranges.append((current_start, min(source_duration_ms, previous_end + half_pause)))
            current_start = max(0, next_start - (kept_pause_ms - half_pause))
        previous_end = max(previous_end, _to_ms(word.end))

    ranges.append(
        (
            current_start,
            min(source_duration_ms, previous_end + edge_padding_ms),
        )
    )

    timeline: list[TimelineMapSegment] = []
    output_cursor = 0
    for source_start, source_end in ranges:
        if source_end <= source_start:
            continue
        duration = source_end - source_start
        timeline.append(
            TimelineMapSegment(
                source_start_ms=source_start,
                source_end_ms=source_end,
                output_start_ms=output_cursor,
                output_end_ms=output_cursor + duration,
            )
        )
        output_cursor += duration
    return timeline


def remove_isolated_fillers(
    segments: list[TranscriptSegment],
    *,
    min_boundary_gap_ms: int = 80,
    min_confidence: float = 0.8,
) -> list[TranscriptSegment]:
    cleaned: list[TranscriptSegment] = []
    for segment in segments:
        retained: list[TranscriptWord] = []
        for index, word in enumerate(segment.words):
            normalized = re.sub(r"[^a-z]", "", word.text.lower())
            previous_word = segment.words[index - 1] if index > 0 else None
            next_word = (
                segment.words[index + 1]
                if index + 1 < len(segment.words)
                else None
            )
            previous_gap_ms = (
                _to_ms(word.start - previous_word.end)
                if previous_word is not None
                else min_boundary_gap_ms
            )
            next_gap_ms = (
                _to_ms(next_word.start - word.end)
                if next_word is not None
                else min_boundary_gap_ms
            )
            confidence = word.confidence if word.confidence is not None else 0
            is_safe_filler = (
                normalized in _FILLER_WORDS
                and confidence >= min_confidence
                and previous_gap_ms >= min_boundary_gap_ms
                and next_gap_ms >= min_boundary_gap_ms
            )
            if not is_safe_filler:
                retained.append(word)

        if retained:
            cleaned.append(
                TranscriptSegment(
                    start=retained[0].start,
                    end=retained[-1].end,
                    text=" ".join(word.text for word in retained),
                    words=retained,
                )
            )
        elif not segment.words and segment.text.strip():
            cleaned.append(segment)
    return cleaned


def build_caption_pages(
    segments: list[TranscriptSegment],
    *,
    max_words: int = 3,
    family: CaptionFamily = "compact-pill",
) -> list[CaptionPage]:
    pages: list[CaptionPage] = []
    anchor, transition, max_width = _CAPTION_DEFAULTS[family]
    for segment in segments:
        words = segment.words or _words_from_segment_text(segment)
        for sentence in _split_caption_sentences(words):
            for group in _group_caption_sentence(
                sentence,
                max_words=max_words,
            ):
                tokens = [
                    CaptionToken(
                        text=word.text,
                        start_ms=_to_ms(word.start),
                        end_ms=max(_to_ms(word.end), _to_ms(word.start) + 1),
                        highlighted=False,
                        confidence=word.confidence,
                    )
                    for word in group
                ]
                pages.append(
                    CaptionPage(
                        start_ms=tokens[0].start_ms,
                        end_ms=max(token.end_ms for token in tokens),
                        tokens=tokens,
                        family=family,
                        anchor=anchor,
                        transition=transition,
                        max_width=max_width,
                    )
                )
    return pages


def _words_from_segment_text(
    segment: TranscriptSegment,
) -> list[TranscriptWord]:
    tokens = segment.text.split()
    if not tokens:
        return []
    duration = max(0.001, segment.end - segment.start)
    step = duration / len(tokens)
    return [
        TranscriptWord(
            start=segment.start + index * step,
            end=segment.end
            if index == len(tokens) - 1
            else segment.start + (index + 1) * step,
            text=token,
        )
        for index, token in enumerate(tokens)
    ]


def _split_caption_sentences(
    words: list[TranscriptWord],
) -> list[list[TranscriptWord]]:
    sentences: list[list[TranscriptWord]] = []
    current: list[TranscriptWord] = []
    for word in words:
        current.append(word)
        if _TERMINAL_PUNCTUATION.search(word.text):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


def _group_caption_sentence(
    words: list[TranscriptWord],
    *,
    max_words: int,
) -> list[list[TranscriptWord]]:
    groups: list[list[TranscriptWord]] = []
    current: list[TranscriptWord] = []
    index = 0
    while index < len(words):
        unit = _protected_caption_unit(words, index)
        if current and len(current) + len(unit) > max_words:
            grammar_extension = (
                len(current) + len(unit) <= max_words + 1
                and (
                    _CLAUSE_PUNCTUATION.search(unit[-1].text)
                    or _TERMINAL_PUNCTUATION.search(unit[-1].text)
                )
            )
            if not grammar_extension:
                groups.append(current)
                current = []
        current.extend(unit)
        index += len(unit)
        duration = current[-1].end - current[0].start
        clause_end = bool(_CLAUSE_PUNCTUATION.search(current[-1].text))
        sentence_end = bool(_TERMINAL_PUNCTUATION.search(current[-1].text))
        next_unit = (
            _protected_caption_unit(words, index)
            if index < len(words)
            else []
        )
        next_unit_size = len(next_unit)
        next_is_grammar_close = bool(
            next_unit
            and (
                _CLAUSE_PUNCTUATION.search(next_unit[-1].text)
                or _TERMINAL_PUNCTUATION.search(next_unit[-1].text)
            )
        )
        must_break = (
            sentence_end
            or (clause_end and (duration >= 0.35 or len(current) >= 2))
            or (
                len(current) >= max_words
                and not (
                    len(current) + next_unit_size <= max_words + 1
                    and next_is_grammar_close
                )
            )
            or duration >= 1.3
            or (
                current
                and index < len(words)
                and len(current) + next_unit_size > max_words
                and not (
                    len(current) + next_unit_size <= max_words + 1
                    and next_is_grammar_close
                )
            )
        )
        if must_break:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _protected_caption_unit(
    words: list[TranscriptWord],
    index: int,
) -> list[TranscriptWord]:
    word = words[index]
    if _CURRENCY_TOKEN.match(word.text):
        return [word]
    if (
        index + 1 < len(words)
        and _looks_like_name_word(word.text)
        and _looks_like_name_word(words[index + 1].text)
    ):
        end = index + 2
        while (
            end < len(words)
            and end - index < 4
            and _looks_like_name_word(words[end].text)
        ):
            end += 1
        return words[index:end]
    return [word]


def _looks_like_name_word(text: str) -> bool:
    stripped = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", text)
    return bool(
        stripped
        and (
            stripped.isupper()
            or (
                stripped[0].isupper()
                and any(character.islower() for character in stripped[1:])
            )
        )
    )


def build_edit_plan(
    *,
    source_filename: str,
    metadata: VideoMetadata,
    transcript: list[TranscriptSegment],
) -> EditPlanV1:
    source_duration_ms = round(metadata.duration_seconds * 1000)
    cleaned_transcript = remove_isolated_fillers(transcript)
    timeline = build_timeline_map(
        cleaned_transcript,
        source_duration_ms=source_duration_ms,
    )
    retimed_segments = _retime_segments(cleaned_transcript, timeline)
    transcript_text = " ".join(
        segment.text.strip()
        for segment in cleaned_transcript
        if segment.text.strip()
    )
    style_variant = choose_style_variant(transcript_text)
    duration_ms = timeline[-1].output_end_ms
    caption_pages = build_adaptive_caption_pages(
        retimed_segments,
        style_variant=style_variant,
    )
    if style_variant == "technical-explanation":
        scenes, editorial_visuals = _build_technical_storyboard(
            duration_ms,
            caption_pages,
            transcript_text,
        )
    else:
        scenes = _build_scenes(duration_ms, style_variant, caption_pages)
        editorial_visuals = []
    graphics = _build_graphics(
        caption_pages,
        duration_ms,
        style_variant,
        transcript_text,
    )

    return EditPlanV1(
        source_filename=source_filename,
        source_metadata=metadata,
        output=OutputSpec(fps=60 if metadata.fps >= 50 else 30),
        duration_ms=duration_ms,
        style_variant=style_variant,
        timeline=timeline,
        caption_pages=caption_pages,
        scenes=scenes,
        graphics=graphics,
        editorial_visuals=editorial_visuals,
        audio=AudioPlan(),
        qc_targets=_qc_targets_for_variant(style_variant),
    )


def build_adaptive_caption_pages(
    segments: list[TranscriptSegment],
    *,
    style_variant: StyleVariant,
) -> list[CaptionPage]:
    pages: list[CaptionPage] = []
    for index, segment in enumerate(segments):
        normalized = segment.text.lower()
        role = classify_sentence(
            segment.text,
            index=index,
            total=len(segments),
        )
        if role == "evidence" or re.search(r"\b(?:19|20)\d{2}\b", normalized):
            family: CaptionFamily = "documentary-clean"
        elif style_variant == "product-demo" and role == "demonstration":
            family = "outlined-demo"
        elif style_variant == "technical-explanation":
            family = "technical-mono"
        else:
            family = "compact-pill"
        pages.extend(build_caption_pages([segment], family=family))
    return pages


def _build_scenes(
    duration_ms: int,
    style_variant: StyleVariant,
    pages: list[CaptionPage],
) -> list[ScenePlan]:
    target_scene_ms = 2500 if style_variant == "hyper-montage" else 3500
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < duration_ms:
        end = min(duration_ms, start + target_scene_ms)
        ranges.append((start, end))
        start = end

    scenes: list[ScenePlan] = []
    zooms = [1.0, 1.12, 1.24]
    for index, (start, end) in enumerate(ranges):
        scene_text = " ".join(
            token.text
            for page in pages
            if page.start_ms < end and page.end_ms > start
            for token in page.tokens
        )
        role = classify_sentence(
            scene_text,
            index=index,
            total=len(ranges),
        )
        layout = "presenter" if index % 2 == 0 else "graphic"
        scenes.append(
            ScenePlan(
                id=f"scene-{index + 1}",
                start_ms=start,
                end_ms=end,
                role=role,
                layout=layout,
                zoom=zooms[index % len(zooms)],
            )
        )
    return scenes


def _build_technical_storyboard(
    duration_ms: int,
    pages: list[CaptionPage],
    transcript_text: str,
) -> tuple[list[ScenePlan], list[EditorialVisual]]:
    boundaries = _technical_scene_boundaries(duration_ms, pages)
    scenes: list[ScenePlan] = []
    visuals: list[EditorialVisual] = []
    seen_kinds: set[str] = set()
    previous_visual_kind: str | None = None
    zooms = [1.0, 1.12, 1.24]

    for index, (start_ms, end_ms) in enumerate(
        zip(boundaries, boundaries[1:])
    ):
        scene_text = _text_for_range(pages, start_ms, end_ms)
        role = classify_sentence(
            scene_text,
            index=index,
            total=len(boundaries) - 1,
        )
        is_hook = index == 0
        is_ending = index == len(boundaries) - 2
        if is_hook or is_ending:
            scenes.append(
                ScenePlan(
                    id=f"scene-{index + 1}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    role=role,
                    layout="presenter",
                    zoom=zooms[index % len(zooms)],
                )
            )
            previous_visual_kind = None
            continue

        visual = _technical_visual_for_text(
            scene_text,
            transcript_text,
            index=index,
            start_ms=start_ms,
            end_ms=end_ms,
            previous_kind=previous_visual_kind,
        )
        should_reset_to_presenter = (
            (
                index % 3 == 0
                and visual.kind in seen_kinds
            )
            or (
                visual.kind == "chat-cta"
                and previous_visual_kind == "chat-cta"
            )
        )
        if should_reset_to_presenter:
            scenes.append(
                ScenePlan(
                    id=f"scene-{index + 1}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    role=role,
                    layout="presenter",
                    zoom=zooms[index % len(zooms)],
                )
            )
            previous_visual_kind = None
            continue

        seen_kinds.add(visual.kind)
        previous_visual_kind = visual.kind
        visuals.append(visual)
        scenes.append(
            ScenePlan(
                id=f"scene-{index + 1}",
                start_ms=start_ms,
                end_ms=end_ms,
                role=role,
                layout=_layout_for_technical_visual(visual.kind, index),
                zoom=zooms[index % len(zooms)],
                visual_id=visual.id,
            )
        )
    return scenes, visuals


def _technical_scene_boundaries(
    duration_ms: int,
    pages: list[CaptionPage] | None = None,
) -> list[int]:
    if duration_ms <= 2200:
        return [0, duration_ms]
    ending_ms = 700 if duration_ms >= 5000 else 500
    body_end = duration_ms - ending_ms
    if pages:
        ordered_tokens = sorted(
            (
                token
                for page in pages
                for token in page.tokens
                if 0 <= token.start_ms < body_end
            ),
            key=lambda token: (token.start_ms, token.end_ms),
        )
        unsafe_boundaries = {
            current.start_ms
            for previous, current in zip(
                ordered_tokens,
                ordered_tokens[1:],
            )
            if (
                any(character.isdigit() for character in previous.text)
                and re.sub(r"[^a-z%]", "", current.text.lower())
                in {
                    "billion",
                    "dollar",
                    "dollars",
                    "million",
                    "percent",
                    "percentage",
                    "%",
                }
            )
        }
        word_starts = sorted(
            {
                token.start_ms
                for token in ordered_tokens
                if 0 < token.start_ms < body_end
                and token.start_ms not in unsafe_boundaries
            }
        )
        boundaries = [0]
        while body_end - boundaries[-1] >= 2200:
            minimum = boundaries[-1] + 1500
            maximum = min(boundaries[-1] + 3000, body_end - 1000)
            candidates = [
                time_ms
                for time_ms in word_starts
                if minimum <= time_ms <= maximum
            ]
            if not candidates:
                break
            target = boundaries[-1] + 2400
            boundary = min(
                candidates,
                key=lambda time_ms: abs(time_ms - target),
            )
            boundaries.append(boundary)
        if body_end - boundaries[-1] < 1000 and len(boundaries) > 1:
            boundaries.pop()
        boundaries.append(body_end)
        boundaries.append(duration_ms)
        return boundaries

    boundaries = [0]
    while boundaries[-1] < body_end:
        boundaries.append(min(body_end, boundaries[-1] + 2400))
    if (
        len(boundaries) >= 3
        and boundaries[-1] - boundaries[-2] < 1000
    ):
        boundaries.pop(-2)
    if boundaries[-1] != duration_ms:
        boundaries.append(duration_ms)
    return boundaries


def _text_for_range(
    pages: list[CaptionPage],
    start_ms: int,
    end_ms: int,
) -> str:
    return " ".join(
        token.text
        for page in pages
        if page.start_ms < end_ms and page.end_ms > start_ms
        for token in page.tokens
        if token.start_ms < end_ms and token.end_ms > start_ms
    )


def _technical_visual_for_text(
    text: str,
    transcript_text: str,
    *,
    index: int,
    start_ms: int,
    end_ms: int,
    previous_kind: str | None,
) -> EditorialVisual:
    normalized = text.lower()
    full_text = transcript_text.lower()
    trading_story = any(
        term in full_text
        for term in {"forex", "trading", "expert advisor"}
    )
    if index == 1 and trading_story:
        kind = "trading-chart"
    elif any(
        term in normalized
        for term in {"telegram", "join", "follow", "live", "group"}
    ):
        kind = "chat-cta"
    elif _contains_metric(normalized):
        kind = "metric-reveal"
    elif (
        "rules" in normalized
        and re.search(r"\b(?:19|20)\d{2}\b", normalized)
    ):
        kind = "rule-flow"
    elif (
        "championship" in normalized
        and "expert advisor" in normalized
    ):
        kind = "code-terminal"
    elif re.search(r"\b(?:19|20)\d{2}\b", normalized) or any(
        term in normalized
        for term in {"championship", "evidence", "report", "study"}
    ):
        kind = "evidence-card"
    elif any(
        term in normalized
        for term in {
            "risk",
            "drawdown",
            "loss",
            "ulta",
            "palat",
            "crash",
            "upside",
            "safe",
        }
    ):
        kind = "risk-meter"
    elif any(
        term in normalized
        for term in {"emotion", "lesson", "fear", "greed"}
    ):
        kind = "comparison"
    elif any(
        term in normalized
        for term in {"rules", "automatically", "decision", "logic"}
    ):
        kind = "rule-flow"
    elif any(
        term in normalized
        for term in {"expert advisor", "software", "code", "program", "ea"}
    ):
        kind = "code-terminal"
    elif trading_story and any(
        term in normalized
        for term in {"forex", "trading", "trade", "robot", "market"}
    ):
        kind = "trading-chart"
    else:
        kind = (
            "code-terminal",
            "rule-flow",
            "trading-chart",
        )[index % 3]

    if kind == previous_kind:
        kind = {
            "code-terminal": "rule-flow",
            "rule-flow": "code-terminal",
            "evidence-card": "code-terminal",
            "metric-reveal": "risk-meter",
            "risk-meter": "trading-chart",
            "comparison": "rule-flow",
        }.get(kind, kind)

    title, subtitle, value, items, direction = _technical_visual_copy(
        kind,
        normalized,
        full_text,
        trading_story=trading_story,
    )
    return EditorialVisual(
        id=f"editorial-{index + 1}",
        start_ms=start_ms,
        end_ms=end_ms,
        kind=kind,
        title=title,
        subtitle=subtitle,
        value=value,
        items=items,
        direction=direction,
    )


def _contains_metric(text: str) -> bool:
    has_currency_symbol = any(
        symbol in text for symbol in {"$", "€", "£", "₹"}
    )
    return bool(
        re.search(r"(?:[$€£₹]\s*)?\d[\d,]*(?:\.\d+)?", text)
        and (
            has_currency_symbol
            or any(
                term in text
                for term in {
                    "dollar",
                    "earn",
                    "profit",
                    "percent",
                    "%",
                    "million",
                    "billion",
                }
            )
        )
    )


def _technical_visual_copy(
    kind: str,
    scene_text: str,
    full_text: str,
    *,
    trading_story: bool,
) -> tuple[str, str, str | None, list[str], str]:
    if kind == "trading-chart":
        falling = any(
            term in scene_text
            for term in {
                "risk",
                "loss",
                "ulta",
                "palat",
                "crash",
                "upside",
            }
        )
        return (
            "FOREX MARKET AUTOMATION"
            if trading_story
            else "LIVE SYSTEM SIGNAL",
            "Software watches data and executes a defined action",
            None,
            ["MARKET DATA", "ENTRY RULE", "ORDER"],
            "down" if falling else "up",
        )
    if kind == "rule-flow":
        return (
            "FIXED RULES -> AUTOMATED ACTION",
            "The system follows logic - not instinct",
            None,
            ["READ DATA", "CHECK RULES", "BUY / HOLD / SELL"],
            "neutral",
        )
    if kind == "code-terminal":
        return (
            "EXPERT ADVISOR (EA)"
            if trading_story
            else "THE DECISION ENGINE",
            "A rules-based program running every decision",
            None,
            [
                "if (signal && risk <= limit)",
                "executeTrade();",
                "setStopLoss();",
            ],
            "neutral",
        )
    if kind == "evidence-card":
        year_match = re.search(r"\b(?:19|20)\d{2}\b", scene_text)
        year = year_match.group(0) if year_match else "CASE"
        return (
            f"{year} AUTOMATED TRADING CHAMPIONSHIP"
            if trading_story
            else f"{year} EVIDENCE",
            "A real-world stress test for automated decisions",
            year if year != "CASE" else None,
            ["PERFORMANCE", "RULES", "RISK"],
            "neutral",
        )
    if kind == "metric-reveal":
        return (
            "A REPORTED PEAK",
            "Exact values remain hidden until a verified source is attached",
            None,
            ["SOURCE REQUIRED", "AUTOMATED", "RISK"],
            "up",
        )
    if kind == "risk-meter":
        negative = any(
            term in scene_text
            for term in {"loss", "ulta", "palat", "crash", "drawdown"}
        )
        return (
            "HIGHER RETURN. HIGHER RISK.",
            "The same aggression can amplify losses",
            "RISK UP",
            ["RETURN", "EXPOSURE", "DRAWDOWN"],
            "down" if negative else "up",
        )
    if kind == "comparison":
        return (
            "NO EMOTION != SAFE RISK",
            "Automation removes impulse, not bad parameters",
            None,
            ["NO FEAR / GREED", "FIXED RULES", "RISK STILL MATTERS"],
            "neutral",
        )
    return (
        "WATCH THE EA LIVE"
        if trading_story
        else "FOLLOW THE LIVE SYSTEM",
        "Telegram updates for entries, exits and risk",
        None,
        ["LIVE TRADES", "RISK NOTES", "ENTRY / EXIT"],
        "neutral",
    )


def _layout_for_technical_visual(kind: str, index: int) -> str:
    if kind == "code-terminal":
        return "split-screen"
    if kind == "rule-flow":
        return "presenter-pip"
    if kind == "trading-chart" and index % 2 == 0:
        return "presenter-pip"
    return "graphic"


def _build_graphics(
    pages: list[CaptionPage],
    duration_ms: int,
    style_variant: StyleVariant,
    transcript_text: str,
) -> list[GraphicCue]:
    if not pages:
        return []
    if (
        style_variant == "technical-explanation"
        and any(
            term in transcript_text.lower()
            for term in {"forex", "trading", "expert advisor"}
        )
    ):
        headline = "CAN A FOREX ROBOT CONTROL RISK?"
    elif style_variant == "technical-explanation":
        headline = "HOW THE SYSTEM REALLY WORKS"
    else:
        headline = " ".join(token.text for token in pages[0].tokens)
    hook_target = min(1500, max(900, round(duration_ms * 0.32)))
    hook_end = min(duration_ms, max(1, snap_to_beat_ms(hook_target)))
    graphics = [
        GraphicCue(
            id="graphic-hook",
            start_ms=0,
            end_ms=hook_end,
            kind="headline",
            text=headline,
        )
    ]
    if style_variant == "technical-explanation":
        return graphics
    template_kind = {
        "tech-news": "browser",
        "cinematic-concept": "callout",
        "technical-explanation": "label",
        "product-demo": "phone",
        "hardware-launch": "label",
        "hyper-montage": "counter",
    }[style_variant]
    clean_ending_ms = min(700, max(400, round(duration_ms * 0.15)))
    if duration_ms > hook_end + clean_ending_ms:
        template_tokens = pages[min(1, len(pages) - 1)].tokens
        template_start = min(
            max(hook_end, snap_to_beat_ms(hook_end + 100)),
            duration_ms - clean_ending_ms - 1,
        )
        template_end = min(
            duration_ms - clean_ending_ms,
            template_start + 1600,
        )
        graphics.append(
            GraphicCue(
                id="graphic-template",
                start_ms=template_start,
                end_ms=template_end,
                kind=template_kind,
                text=" ".join(token.text for token in template_tokens),
                accent="#00E5FF"
                if style_variant == "technical-explanation"
                else "#D7FF64",
            )
        )
    for index, page in enumerate(pages[4::5], start=1):
        start_ms = min(
            max(1, snap_to_beat_ms(page.start_ms)),
            duration_ms - 1,
        )
        graphics.append(
            GraphicCue(
                id=f"graphic-callout-{index}",
                start_ms=start_ms,
                end_ms=min(duration_ms, page.end_ms + 650),
                kind="callout",
                text=" ".join(token.text for token in page.tokens),
            )
        )
    return graphics


def _retime_segments(
    segments: list[TranscriptSegment],
    timeline: list[TimelineMapSegment],
) -> list[TranscriptSegment]:
    retimed: list[TranscriptSegment] = []
    for segment in segments:
        words: list[TranscriptWord] = []
        previous_start_ms = -1
        for word in segment.words:
            mapped_start = _map_source_ms(_to_ms(word.start), timeline)
            mapped_end = _map_source_ms(_to_ms(word.end), timeline)
            if mapped_start is None or mapped_end is None:
                continue
            start = max(mapped_start, previous_start_ms)
            if start >= timeline[-1].output_end_ms:
                continue
            end = min(
                timeline[-1].output_end_ms,
                max(mapped_end, start + 1),
            )
            if end <= start:
                continue
            words.append(
                TranscriptWord(
                    start=start / 1000,
                    end=end / 1000,
                    text=word.text,
                    confidence=word.confidence,
                )
            )
            previous_start_ms = start
        if words:
            retimed.append(
                TranscriptSegment(
                    start=words[0].start,
                    end=words[-1].end,
                    text=" ".join(word.text for word in words),
                    words=words,
                )
            )
    return retimed


def _map_source_ms(
    source_ms: int,
    timeline: list[TimelineMapSegment],
) -> int | None:
    for segment in timeline:
        if segment.source_start_ms <= source_ms <= segment.source_end_ms:
            return segment.output_start_ms + source_ms - segment.source_start_ms
    return None


def _flatten_words(segments: list[TranscriptSegment]) -> list[TranscriptWord]:
    words = [word for segment in segments for word in segment.words if word.text.strip()]
    return sorted(words, key=lambda word: (word.start, word.end))


def _to_ms(seconds: float) -> int:
    return round(seconds * 1000)
