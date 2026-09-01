from pathlib import Path
from types import SimpleNamespace

from app.editor import pipeline
from app.editor.transcript import (
    clean_transcript,
    repair_nonpositive_word_durations,
    retime_corrected_segments,
)
from app.models import TranscriptSegment, TranscriptWord


def source_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=0,
            end=2,
            text="Exported Wiser trades emotion",
            words=[
                TranscriptWord(start=0, end=0.5, text="Exported"),
                TranscriptWord(start=0.5, end=1, text="Wiser"),
                TranscriptWord(start=1, end=1.5, text="trades"),
                TranscriptWord(start=1.5, end=2, text="emotion"),
            ],
        ),
        TranscriptSegment(
            start=2,
            end=4,
            text="join instagram group",
            words=[],
        ),
    ]


def test_retime_corrected_segments_preserves_matched_word_timestamps() -> None:
    corrected = retime_corrected_segments(
        source_segments(),
        ["Expert Advisor trades without emotion.", "Join our Telegram group."],
    )

    assert corrected[0].start == 0
    assert corrected[0].end == 2
    assert corrected[0].text == "Expert Advisor trades without emotion."
    assert [word.text for word in corrected[0].words] == [
        "Expert",
        "Advisor",
        "trades",
        "without",
        "emotion.",
    ]
    assert corrected[0].words[2].start == 1
    assert corrected[0].words[2].end == 1.5
    assert corrected[0].words[-1].start == 1.5
    assert corrected[0].words[-1].end == 2


def test_retime_corrected_segments_only_interpolates_inserted_tokens() -> None:
    original = [
        TranscriptSegment(
            start=0,
            end=2,
            text="It trades on rules",
            words=[
                TranscriptWord(start=0, end=0.3, text="It"),
                TranscriptWord(start=0.3, end=0.8, text="trades"),
                TranscriptWord(start=1.1, end=1.35, text="on"),
                TranscriptWord(start=1.35, end=2, text="rules"),
            ],
        )
    ]

    corrected = retime_corrected_segments(
        original,
        ["It trades based on rules."],
    )[0]

    by_text = {word.text: word for word in corrected.words}
    assert (by_text["It"].start, by_text["It"].end) == (0, 0.3)
    assert (by_text["trades"].start, by_text["trades"].end) == (0.3, 0.8)
    assert (by_text["on"].start, by_text["on"].end) == (1.1, 1.35)
    assert (by_text["rules."].start, by_text["rules."].end) == (1.35, 2)
    assert (by_text["based"].start, by_text["based"].end) == (0.8, 1.1)


def test_retime_corrected_segments_merges_split_currency_without_redistribution() -> None:
    original = [
        TranscriptSegment(
            start=0,
            end=2,
            text="earned $110 ,000.",
            words=[
                TranscriptWord(start=0, end=0.4, text="earned"),
                TranscriptWord(start=0.4, end=1.1, text="$110"),
                TranscriptWord(start=1.1, end=2, text=",000."),
            ],
        )
    ]

    corrected = retime_corrected_segments(
        original,
        ["earned $110,000."],
    )[0]

    assert [word.text for word in corrected.words] == [
        "earned",
        "$110,000.",
    ]
    assert corrected.words[0].start == 0
    assert corrected.words[0].end == 0.4
    assert corrected.words[1].start == 0.4
    assert corrected.words[1].end == 2


def test_repair_nonpositive_word_durations_preserves_valid_source_words() -> None:
    segment = TranscriptSegment(
        start=0,
        end=1,
        text="trades on set rules",
        words=[
            TranscriptWord(start=0, end=1, text="trades"),
            TranscriptWord(start=1, end=1, text="on"),
            TranscriptWord(start=1, end=1, text="set"),
            TranscriptWord(start=1, end=1, text="rules"),
        ],
    )

    repaired = repair_nonpositive_word_durations([segment])[0]

    assert (repaired.words[0].start, repaired.words[0].end) == (0, 1)
    assert all(word.end > word.start for word in repaired.words)
    assert repaired.words[-1].end <= segment.end


def test_clean_transcript_uses_valid_same_length_json_response() -> None:
    corrected = clean_transcript(
        source_segments(),
        requester=lambda _prompt: (
            '["Expert Advisor trades without emotion.",'
            ' "Join our Telegram group."]'
        ),
    )

    assert [segment.text for segment in corrected] == [
        "Expert Advisor trades without emotion.",
        "Join our Telegram group.",
    ]


def test_clean_transcript_falls_back_when_response_is_invalid() -> None:
    original = source_segments()

    corrected = clean_transcript(original, requester=lambda _prompt: "not json")

    assert corrected == original


def test_retime_corrected_segments_keeps_source_for_placeholder_text() -> None:
    original = source_segments()

    corrected = retime_corrected_segments(
        original,
        ["...", "Join our Telegram group."],
    )

    assert corrected[0] == original[0]
    assert corrected[1].text == "Join our Telegram group."


def test_clean_transcript_prompt_forbids_omissions() -> None:
    prompts: list[str] = []

    def requester(prompt: str) -> str:
        prompts.append(prompt)
        return '["Expert Advisor trades without emotion.", "Join us."]'

    clean_transcript(source_segments(), requester=requester)

    assert "Never omit spoken content" in prompts[0]
    assert "preserve the input verbatim" in prompts[0]
    assert "Latin-script Hinglish" in prompts[0]


def test_clean_transcript_rejects_over_compressed_correction() -> None:
    original = [
        TranscriptSegment(
            start=0,
            end=5,
            text=(
                "Expert Advisor follows fixed rules automatically and the "
                "same aggressive settings can later reverse the result"
            ),
            words=[],
        )
    ]

    corrected = clean_transcript(
        original,
        requester=lambda _prompt: '["Expert Advisor follows rules."]',
    )

    assert corrected == original


def test_clean_transcript_rejects_correction_that_drops_numbers() -> None:
    original = [
        TranscriptSegment(
            start=0,
            end=5,
            text=(
                "In 2008 the automated trading result reached 110000 "
                "dollars before risk changed the outcome"
            ),
            words=[],
        )
    ]

    corrected = clean_transcript(
        original,
        requester=lambda _prompt: (
            '["The automated trading result reached a large profit before '
            'risk changed the outcome."]'
        ),
    )

    assert corrected == original


def test_transcribe_video_defaults_to_multilingual_transcription(
    monkeypatch,
) -> None:
    received: dict[str, object] = {}

    class FakeModel:
        def transcribe(self, _path: str, **kwargs):
            received.update(kwargs)
            return iter(()), object()

    monkeypatch.delenv("VIDEO_EDITOR_LANGUAGE", raising=False)
    monkeypatch.setenv("VIDEO_EDITOR_TRANSCRIPT_CLEANUP", "off")
    monkeypatch.setattr(
        pipeline,
        "_load_whisper_model",
        lambda _model_name: FakeModel(),
    )

    assert pipeline.transcribe_video(Path("raw.mp4")) == []
    assert received["language"] is None
    assert received["task"] == "transcribe"
    assert "temperature" not in received


def test_transcribe_video_retries_corrupt_auto_detection_in_english(
    monkeypatch,
) -> None:
    languages: list[str | None] = []

    class FakeModel:
        def transcribe(self, _path: str, **kwargs):
            language = kwargs["language"]
            languages.append(language)
            if language is None:
                segment = SimpleNamespace(
                    start=0,
                    end=2,
                    text="���� गलत प्रतिलेख",
                    words=[
                        SimpleNamespace(
                            start=0,
                            end=1,
                            word="����",
                            probability=0.2,
                        )
                    ],
                )
            else:
                segment = SimpleNamespace(
                    start=0,
                    end=2,
                    text="Forex trading robot follows fixed rules.",
                    words=[
                        SimpleNamespace(
                            start=0,
                            end=0.5,
                            word="Forex",
                            probability=0.95,
                        ),
                        SimpleNamespace(
                            start=0.5,
                            end=1,
                            word="trading",
                            probability=0.95,
                        ),
                        SimpleNamespace(
                            start=1,
                            end=1.5,
                            word="robot",
                            probability=0.95,
                        ),
                        SimpleNamespace(
                            start=1.5,
                            end=2,
                            word="rules",
                            probability=0.95,
                        ),
                    ],
                )
            return iter([segment]), object()

    monkeypatch.delenv("VIDEO_EDITOR_LANGUAGE", raising=False)
    monkeypatch.setenv("VIDEO_EDITOR_TRANSCRIPT_CLEANUP", "off")
    monkeypatch.setattr(
        pipeline,
        "_load_whisper_model",
        lambda _model_name: FakeModel(),
    )

    segments = pipeline.transcribe_video(Path("raw.mp4"))

    assert languages == [None, "en"]
    assert segments[0].text == "Forex trading robot follows fixed rules."


def test_fixed_language_transcription_bypasses_auto_detection_and_cleanup(
    monkeypatch,
) -> None:
    received: dict[str, object] = {}

    class FakeModel:
        def transcribe(self, _path: str, **kwargs):
            received.update(kwargs)
            return iter(()), object()

    monkeypatch.setattr(
        pipeline,
        "_load_whisper_model",
        lambda _model_name: FakeModel(),
    )
    monkeypatch.setattr(
        pipeline,
        "_clean_transcript_if_configured",
        lambda _segments: (_ for _ in ()).throw(
            AssertionError("Review transcription must not call cleanup")
        ),
    )

    assert pipeline.transcribe_video_fixed_language(
        Path("review.mp4"),
        language="en",
    ) == []
    assert received["language"] == "en"
    assert received["task"] == "transcribe"


def test_configured_cleanup_disables_response_storage(monkeypatch) -> None:
    captured: dict[str, object] = {}
    client_config: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "output_text": (
                        '["Expert Advisor trades without emotion.",'
                        ' "Join our Telegram group."]'
                    )
                },
            )()

    class FakeClient:
        def __init__(self, **kwargs):
            client_config.update(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.invalid/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_GPT56_SOL_DEPLOYMENT", "test-deployment")
    monkeypatch.setattr("openai.OpenAI", FakeClient)

    corrected = pipeline._clean_transcript_if_configured(source_segments())

    assert corrected[0].text == "Expert Advisor trades without emotion."
    assert captured["store"] is False
    assert client_config["timeout"] == 120
