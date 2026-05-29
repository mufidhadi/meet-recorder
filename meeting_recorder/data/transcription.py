from pydantic import BaseModel
from typing import List

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str

class TranscriptResult(BaseModel):
    segments: List[TranscriptSegment]
    full_text: str
