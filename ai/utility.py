"""Utility-based decision making: score every possible action (0..1), pick the highest."""
from config import CFG

CHASE, INVESTIGATE, SEARCH, PATROL = "CHASE", "INVESTIGATE", "SEARCH", "PATROL"

U = CFG["utility"]


def score_actions(inp, current_action):
    """
    inp keys:
      visible (bool)          player is in view right now
      proximity (0..1)        1 = player right next to us, 0 = at the edge of vision
      sound (0..1)            loudness of the loudest noise heard now (0 = silence)
      memory (0..1)           how fresh the last-known-position memory is
      recent_contact (0/1)    player was seen within the last second
      suspicion (0..1)        built up by seeing/hearing things, decays slowly
      pending_investigation   already walking to / looking around at a noise spot
    Returns {action: score}.
    """
    visible = 1.0 if inp["visible"] else 0.0

    # CHASE: strong when the player is visible; keeps going briefly after losing sight
    chase = visible * (U["chase_base"] + U["chase_proximity"] * inp["proximity"]) \
        + (1.0 - visible) * inp["recent_contact"] * U["chase_recent"]

    # INVESTIGATE: louder (closer) noise and more suspicion -> higher
    investigate = 0.0
    if inp["sound"] > 0:
        investigate = (U["investigate_base"] + U["investigate_sound"] * inp["sound"]
                       + U["investigate_suspicion"] * inp["suspicion"])
    if inp["pending_investigation"]:
        investigate = max(investigate, U["investigate_pending"])   # finish checking the spot
    investigate = min(investigate, U["investigate_cap"])           # a visible player always wins

    # SEARCH: fresh memory of where the player was, plus suspicion
    search = inp["memory"] * (U["search_base"] + U["search_suspicion"] * inp["suspicion"])

    # PATROL: baseline, a little lower when suspicious
    patrol = U["patrol_base"] + U["patrol_calm"] * (1.0 - inp["suspicion"])

    scores = {CHASE: chase, INVESTIGATE: investigate, SEARCH: search, PATROL: patrol}
    scores[current_action] += U["commit_bonus"]
    return scores


def choose_action(scores):
    """Highest score wins (ties go to the more urgent action, because of dict order)."""
    return max(scores, key=scores.get)