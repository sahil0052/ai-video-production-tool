from collections.abc import Callable
from difflib import SequenceMatcher
import json
import re

from app.models import TranscriptSegment, TranscriptWord


def repair_nonpositive_word_durations(
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    repaired_segments: list[TranscriptSegment] = []
    for segment in segments:
        words = list(segment.words)
        index = 0
        while index < len(words):
            if words[index].end > words[index].start:
                index += 1
                continue
            cluster_start = index
            while (
                index < len(words)
                and words[index].end <= words[index].start
            ):
                index += 1
            cluster_end = index
            count = cluster_end - cluster_start
            anchor = words[cluster_start].start
            following = (
                words[cluster_end]
                if cluster_end < len(words)
                else None
            )
            previous = (
                words[cluster_start - 1]
                if cluster_start > 0
                else None
            )
            if following is not None and following.start <= anchor:
                left = max(segment.start, anchor)
                right = min(
                    segment.end,
                    max(
                        following.end,
                        anchor + 0.04 * count,
                    ),
                    anchor + 0.08 * count,
                )
            elif following is not None:
                left = max(segment.start, anchor)
                right = min(segment.end, following.start)
            else:
                right = segment.end
                left = max(
                    segment.start,
                    previous.start if previous is not None else segment.start,
                    right - 0.06 * count,
                )
            if right <= left:
                right = min(segment.end, left + 0.001 * count)
            if right <= left:
                left = max(segment.start, segment.end - 0.001 * count)
                right = segment.end
            step = (right - left) / count
            for offset, word_index in enumerate(
                range(cluster_start, cluster_end)
            ):
                start = left + step * offset
                end = (
                    right
                    if offset == count - 1
                    else left + step * (offset + 1)
                )
                words[word_index] = words[word_index].model_copy(
                    update={"start": start, "end": end}
                )
        repaired_segments.append(
            segment.model_copy(update={"words": words})
        )
    return repaired_segments


def retime_corrected_segments(
    segments: list[TranscriptSegment],
    corrected_texts: list[str],
) -> list[TranscriptSegment]:
    if len(segments) != len(corrected_texts):
        return segments

    corrected: list[TranscriptSegment] = []
    for segment, corrected_text in zip(segments, corrected_texts, strict=True):
        text = " ".join(corrected_text.split())
        tokens = text.split()
        if not text or not tokens:
            return segments
        if not any(character.isalnum() for character in text):
            corrected.append(segment)
            continue
        words = _align_corrected_tokens(segment, tokens)
        corrected.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=text,
                words=words,
            )
        )
    return corrected


def _normalize_token(text: str) -> str:
    return "".join(character for character in text.casefold() if character.isalnum())


def _merge_split_source_tokens(
    words: list[TranscriptWord],
) -> list[TranscriptWord]:
    merged: list[TranscriptWord] = []
    index = 0
    while index < len(words):
        current = words[index]
        if (
            index + 1 < len(words)
            and current.text.lstrip().startswith(("$", "€", "£", "₹"))
            and re.fullmatch(r"[\s,._-]*\d[\d,._-]*[.!?]?", words[index + 1].text)
        ):
            following = words[index + 1]
            merged.append(
                TranscriptWord(
                    start=current.start,
                    end=following.end,
                    text=current.text + following.text,
                    confidence=_minimum_confidence(
                        current.confidence,
                        following.confidence,
                    ),
                )
            )
            index += 2
            continue
        merged.append(current)
        index += 1
    return merged


def _minimum_confidence(
    left: float | None,
    right: float | None,
) -> float | None:
    values = [value for value in (left, right) if value is not None]
    return min(values) if values else None


def _align_corrected_tokens(
    segment: TranscriptSegment,
    corrected_tokens: list[str],
) -> list[TranscriptWord]:
    source_words = _merge_split_source_tokens(segment.words)
    if not source_words:
        return _interpolate_unanchored_tokens(segment, corrected_tokens)

    source_keys = [_normalize_token(word.text) for word in source_words]
    corrected_keys = [_normalize_token(token) for token in corrected_tokens]
    matcher = SequenceMatcher(
        a=source_keys,
        b=corrected_keys,
        autojunk=False,
    )
    aligned: list[TranscriptWord | None] = [None] * len(corrected_tokens)
    inserted_ranges: list[tuple[int, int]] = []

    for tag, source_start, source_end, corrected_start, corrected_end in matcher.get_opcodes():
        source_count = source_end - source_start
        corrected_count = corrected_end - corrected_start
        if tag == "equal":
            for offset in range(corrected_count):
                source = source_words[source_start + offset]
                aligned[corrected_start + offset] = source.model_copy(
                    update={"text": corrected_tokens[corrected_start + offset]}
                )
            continue
        if tag == "replace" and source_count == corrected_count:
            for offset in range(corrected_count):
                source = source_words[source_start + offset]
                aligned[corrected_start + offset] = source.model_copy(
                    update={"text": corrected_tokens[corrected_start + offset]}
                )
            continue
        if corrected_count:
            inserted_ranges.append((corrected_start, corrected_end))

    for corrected_start, corrected_end in inserted_ranges:
        previous = next(
            (
                aligned[index]
                for index in range(corrected_start - 1, -1, -1)
                if aligned[index] is not None
            ),
            None,
        )
        following = next(
            (
                aligned[index]
                for index in range(corrected_end, len(aligned))
                if aligned[index] is not None
            ),
            None,
        )
        range_start = previous.end if previous is not None else segment.start
        range_end = following.start if following is not None else segment.end
        if range_end < range_start:
            range_end = range_start
        count = corrected_end - corrected_start
        step = (range_end - range_start) / count if count else 0
        for offset, index in enumerate(range(corrected_start, corrected_end)):
            start = range_start + offset * step
            end = range_end if offset == count - 1 else range_start + (offset + 1) * step
            aligned[index] = TranscriptWord(
                start=start,
                end=end,
                text=corrected_tokens[index],
            )

    if any(word is None for word in aligned):
        return _interpolate_unanchored_tokens(segment, corrected_tokens)
    return [word for word in aligned if word is not None]


def _interpolate_unanchored_tokens(
    segment: TranscriptSegment,
    tokens: list[str],
) -> list[TranscriptWord]:
    duration = max(0.01, segment.end - segment.start)
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


def clean_transcript(
    segments: list[TranscriptSegment],
    *,
    requester: Callable[[str], str],
) -> list[TranscriptSegment]:
    if not segments:
        return segments
    payload = [
        {"start": item.start, "end": item.end, "text": item.text}
        for item in segments
    ]
    prompt = (
        "Correct this noisy automatic transcript of one continuous English/"
        "Hindi/Hinglish talking-head video. Keep spoken Hinglish as natural "
        "Latin-script Hinglish instead of translating it. Preserve meaning, "
        "numbers, names, acronyms and calls to action. Never omit spoken content "
        "or replace speech with ellipses. Do not add claims. If a phrase is "
        "uncertain, preserve the input verbatim. Keep the exact same number and "
        "order of segments. Return only a JSON array of corrected strings, one "
        "string per input segment.\nInput:\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        response = json.loads(requester(prompt))
    except (ValueError, TypeError):
        return segments
    if (
        not isinstance(response, list)
        or len(response) != len(segments)
        or not all(isinstance(item, str) and item.strip() for item in response)
    ):
        return segments
    if not _correction_preserves_content(segments, response):
        return segments
    return retime_corrected_segments(segments, response)


def _correction_preserves_content(
    segments: list[TranscriptSegment],
    corrected_texts: list[str],
) -> bool:
    original_text = " ".join(segment.text for segment in segments)
    corrected_text = " ".join(corrected_texts)
    original_tokens = re.findall(r"[a-z0-9]+", original_text.lower())
    corrected_tokens = re.findall(r"[a-z0-9]+", corrected_text.lower())
    if original_tokens:
        token_ratio = len(corrected_tokens) / len(original_tokens)
        if token_ratio < 0.72 or token_ratio > 1.6:
            return False

    def numeric_tokens(text: str) -> set[str]:
        return {
            "".join(character for character in match if character.isdigit())
            for match in re.findall(r"\d[\d,._-]*", text)
        }

    return numeric_tokens(original_text).issubset(
        numeric_tokens(corrected_text)
    )
