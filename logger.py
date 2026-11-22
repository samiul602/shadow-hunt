import csv
import math
from datetime import datetime
from pathlib import Path

FIELDS = ["t", "event", "detail", "hunter_state", "hunter_x", "hunter_y",
          "player_x", "player_y", "distance", "suspicion",
          "u_chase", "u_investigate", "u_search", "u_patrol", "hidden", "sprinting"]


class EventLogger:
    """Writes one CSV row per game event, so runs can be analysed afterwards."""

    def __init__(self):
        folder = Path(__file__).parent / "logs"
        folder.mkdir(exist_ok=True)
        name = datetime.now().strftime("session_%Y%m%d_%H%M%S.csv")
        self.file = open(folder / name, "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=FIELDS)
        self.writer.writeheader()
        self.t = 0.0   # game time in seconds (only counts while the game is running)

    def tick(self, dt):
        self.t += dt

    def log(self, event, detail, hunter, player):
        px, py = player.pos.x, player.pos.y
        s = hunter.scores
        self.writer.writerow({
            "t": round(self.t, 2),
            "event": event,
            "detail": detail,
            "hunter_state": hunter.state,
            "hunter_x": round(hunter.x), "hunter_y": round(hunter.y),
            "player_x": round(px), "player_y": round(py),
            "distance": round(math.hypot(hunter.x - px, hunter.y - py)),
            "suspicion": round(hunter.suspicion, 2),
            "u_chase": round(s["CHASE"], 2),
            "u_investigate": round(s["INVESTIGATE"], 2),
            "u_search": round(s["SEARCH"], 2),
            "u_patrol": round(s["PATROL"], 2),
            "hidden": int(player.hidden),
            "sprinting": int(player.sprinting),
        })
        self.file.flush()   # write immediately, so nothing is lost if the game crashes

    def close(self):
        self.file.close()