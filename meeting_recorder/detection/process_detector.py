import psutil
from dataclasses import dataclass

MEETING_PROCESSES = {
    # (nama_proses, platform, nama_display)
    "zoom":                    ("all",     "Zoom"),
    "zoom.exe":                ("Windows", "Zoom"),
    "zoomus":                  ("Darwin",  "Zoom"),
    "ms-teams":                ("all",     "Microsoft Teams"),
    "ms-teams.exe":            ("Windows", "Microsoft Teams"),
    "teams":                   ("Linux",   "Microsoft Teams"),
    "webex":                   ("all",     "Cisco Webex"),
    "CiscoWebexMeetings.exe":  ("Windows", "Cisco Webex"),
    "Discord.exe":             ("Windows", "Discord"),
    "discord":                 ("Linux",   "Discord"),
    "slack.exe":               ("Windows", "Slack"),
    "Skype.exe":               ("Windows", "Skype"),
}

@dataclass
class ProcessMatch:
    process_name: str
    app_name: str
    pid: int
    score: int = 40

class ProcessDetector:
    def detect(self) -> list[ProcessMatch]:
        matches = []
        try:
            # Get only name and pid to be fast
            for proc in psutil.process_iter(["name", "pid"]):
                name = proc.info['name']
                if name in MEETING_PROCESSES:
                    platform, app_name = MEETING_PROCESSES[name]
                    matches.append(ProcessMatch(
                        process_name=name,
                        app_name=app_name,
                        pid=proc.info['pid'],
                    ))
        except Exception:
            pass
        return matches
