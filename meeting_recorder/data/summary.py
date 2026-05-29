from pydantic import BaseModel

class MeetingSummary(BaseModel):
    title: str
    raw_markdown: str
