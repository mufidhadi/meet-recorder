import numpy as np
import pytest
from meeting_recorder.ai.aggregator import TranscriptAggregator
from meeting_recorder.data.transcription import TranscriptSegment, TranscriptResult

def test_aggregator_add_segments():
    agg = TranscriptAggregator()
    
    # Chunk 1 (0s - 5s)
    res1 = TranscriptResult(
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Halo"),
            TranscriptSegment(start=2.5, end=4.5, text="Selamat pagi")
        ],
        full_text="Halo Selamat pagi"
    )
    agg.add_result(res1, offset_s=0.0)
    
    # Chunk 2 (5s - 10s)
    res2 = TranscriptResult(
        segments=[
            TranscriptSegment(start=1.0, end=3.0, text="Kita mulai rapat")
        ],
        full_text="Kita mulai rapat"
    )
    agg.add_result(res2, offset_s=5.0)
    
    full_transcript = agg.get_full_transcript()
    assert len(agg.all_segments) == 3
    assert agg.all_segments[2].start == 6.0
    assert "Halo" in full_transcript
    assert "Kita mulai rapat" in full_transcript
