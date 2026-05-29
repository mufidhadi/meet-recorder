import psutil
from dataclasses import dataclass

MEETING_NETWORK_SIGNATURES = [
    {"name": "Zoom",           "ports": {8801, 8802, 3478, 3479}, "score": 25},
    {"name": "MS Teams",       "ports": {3478, 3479, 3480, 3481}, "score": 25},
    {"name": "Google Meet",    "ports": {19302, 19305, 19307},    "score": 25},
    {"name": "WebRTC",         "ports": {3478, 5349},             "score": 15},
    {"name": "Cisco Webex",    "ports": {9000, 5004},             "score": 25},
]

@dataclass
class NetworkMatch:
    remote_address: str
    remote_port: int
    app_name: str
    score: int

class NetworkDetector:
    def detect(self) -> list[NetworkMatch]:
        matches = []
        try:
            connections = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            return []

        active_ports = set()
        for conn in connections:
            if conn.status in ("ESTABLISHED", "SYN_SENT") and conn.raddr:
                active_ports.add(conn.raddr.port)

        for sig in MEETING_NETWORK_SIGNATURES:
            matching_ports = active_ports & sig["ports"]
            if matching_ports:
                matches.append(NetworkMatch(
                    remote_address="",
                    remote_port=next(iter(matching_ports)),
                    app_name=sig["name"],
                    score=sig["score"],
                ))
        return matches
