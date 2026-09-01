from app.editor.captions import build_ass, format_ass_timestamp, make_caption_cues
from app.models import TranscriptSegment, TranscriptWord


def test_make_caption_cues_chunks_word_timestamps() -> None:
    words = [
        TranscriptWord(start=index * 0.25, end=(index + 1) * 0.25, text=word)
        for index, word in enumerate(
            ["Forex", "trading", "robot", "emotion", "में", "trade", "नहीं"]
        )
    ]
    segment = TranscriptSegment(
        start=0,
        end=1.75,
        text="Forex trading robot emotion में trade नहीं",
        words=words,
    )

    cues = make_caption_cues([segment], max_words=4)

    assert [cue.text for cue in cues] == [
        "Forex trading robot emotion",
        "में trade नहीं",
    ]
    assert cues[0].start == 0
    assert cues[0].end == 1
    assert cues[1].start == 1
    assert cues[1].end == 1.75


def test_make_caption_cues_uses_segment_when_words_are_missing() -> None:
    segment = TranscriptSegment(
        start=1.2,
        end=3.4,
        text="Expert Advisor",
        words=[],
    )

    cues = make_caption_cues([segment])

    assert len(cues) == 1
    assert cues[0].text == "Expert Advisor"
    assert cues[0].start == 1.2
    assert cues[0].end == 3.4


def test_format_ass_timestamp_uses_centiseconds() -> None:
    assert format_ass_timestamp(61.236) == "0:01:01.24"


def test_build_ass_preserves_unicode_and_escapes_reserved_characters() -> None:
    segment = TranscriptSegment(
        start=0,
        end=1.5,
        text="EA {emotion} में",
        words=[],
    )
    cue = make_caption_cues([segment])[0]

    output = build_ass([cue], width=1080, height=1920)

    assert "PlayResX: 1080" in output
    assert "PlayResY: 1920" in output
    assert "EA \\{emotion\\} में" in output
    assert "Alignment=2" in output
