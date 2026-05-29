import pytest
from meeting_recorder.ui.models import RecordingSession, TRANSCRIPT_FILENAME, SUMMARY_FILENAME

def test_recording_session_constants():
    assert TRANSCRIPT_FILENAME == "transcript.json"
    assert SUMMARY_FILENAME == "summary.md"

def test_recording_session_formatted_date():
    # Valid session ID
    session = RecordingSession(
        session_id="20260512_143005",
        path="/tmp/20260512_143005",
        has_transcript=True,
        has_summary=True
    )
    assert session.formatted_date == "12 May 2026, 14:30"

    # Invalid session ID (should return as is)
    session = RecordingSession(
        session_id="invalid_id",
        path="/tmp/invalid_id",
        has_transcript=False,
        has_summary=False
    )
    assert session.formatted_date == "invalid_id"

def test_recording_session_formatted_date_edge_cases():
    # Different months
    session = RecordingSession(
        session_id="20260101_000000",
        path="",
        has_transcript=False,
        has_summary=False
    )
    assert session.formatted_date == "01 Jan 2026, 00:00"
    
    session = RecordingSession(
        session_id="20261231_235959",
        path="",
        has_transcript=False,
        has_summary=False
    )
    assert session.formatted_date == "31 Dec 2026, 23:59"
