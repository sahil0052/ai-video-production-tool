from app.models import CaptionCue, TranscriptSegment


def make_caption_cues(
    segments: list[TranscriptSegment], *, max_words: int = 5
) -> list[CaptionCue]:
    cues: list[CaptionCue] = []
    for segment in segments:
        if segment.words:
            for offset in range(0, len(segment.words), max_words):
                group = segment.words[offset : offset + max_words]
                text = " ".join(word.text.strip() for word in group if word.text.strip())
                if text:
                    cues.append(
                        CaptionCue(
                            start=group[0].start,
                            end=group[-1].end,
                            text=text,
                        )
                    )
            continue

        text = " ".join(segment.text.split())
        if text:
            cues.append(CaptionCue(start=segment.start, end=segment.end, text=text))
    return cues


def format_ass_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(total_centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def build_ass(cues: list[CaptionCue], *, width: int, height: int) -> str:
    font_size = max(46, round(width * 0.064))
    margin_vertical = round(height * 0.18)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; Alignment=2
Style: Default,Arial,{font_size},&H00FFFFFF,&H0000D4FF,&H00141414,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,{margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for cue in cues:
        text = (
            cue.text.replace("\\", "\\\\")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace("\n", "\\N")
        )
        events.append(
            "Dialogue: 0,"
            f"{format_ass_timestamp(cue.start)},"
            f"{format_ass_timestamp(cue.end)},"
            f"Default,,0,0,0,,{text}"
        )
    return header + "\n".join(events) + ("\n" if events else "")
