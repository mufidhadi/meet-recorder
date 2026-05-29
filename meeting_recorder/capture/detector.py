import psutil
from typing import List, Optional

class MeetingDetector:
    def __init__(self):
        # Common meeting application process names
        self.target_processes = [
            "Zoom.exe",
            "Teams.exe",
            "ms-teams.exe",
            "CiscoCollabHost.exe", # Webex
            "Discord.exe"
        ]
        # Keywords to look for in browser window titles or process arguments
        self.target_keywords = ["meet.google.com", "zoom.us", "teams.microsoft.com"]

    def is_meeting_active(self) -> bool:
        """Checks if any meeting application is currently running."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                # Check by process name
                if proc.info['name'] in self.target_processes:
                    return True
                
                # Check by command line arguments (common for browser tabs/apps)
                cmdline = proc.info['cmdline']
                if cmdline:
                    cmd_str = " ".join(cmdline).lower()
                    if any(kw in cmd_str for kw in self.target_keywords):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def get_active_meeting_name(self) -> Optional[str]:
        """Returns the name of the detected meeting app."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] in self.target_processes:
                    return proc.info['name']
                
                cmdline = proc.info['cmdline']
                if cmdline:
                    cmd_str = " ".join(cmdline).lower()
                    for kw in self.target_keywords:
                        if kw in cmd_str:
                            return f"Browser ({kw})"
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None
