from typing import List
from meeting_recorder.data.transcription import TranscriptResult, TranscriptSegment

class TranscriptAggregator:
    def __init__(self):
        self.all_segments: List[TranscriptSegment] = []

    def add_result(self, result: TranscriptResult, offset_s: float):
        """Adds a TranscriptResult with a time offset."""
        for segment in result.segments:
            new_segment = TranscriptSegment(
                start=segment.start + offset_s,
                end=segment.end + offset_s,
                text=segment.text
            )
            self.all_segments.append(new_segment)

    def get_full_transcript(self, include_timestamps: bool = True) -> str:
        """Returns the full aggregated transcript text."""
        lines = []
        for s in self.all_segments:
            if include_timestamps:
                # Format: [HH:MM:SS] Text
                h = int(s.start // 3600)
                m = int((s.start % 3600) // 60)
                sec = int(s.start % 60)
                timestamp = f"[{h:02d}:{m:02d}:{sec:02d}]"
                lines.append(f"{timestamp} {s.text}")
            else:
                lines.append(s.text)
        
        return "\n".join(lines)
