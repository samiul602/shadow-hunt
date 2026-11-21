"""Utility-based decision making: score every possible action (0..1), pick the highest."""

CHASE, INVESTIGATE, SEARCH, PATROL = "CHASE", "INVESTIGATE", "SEARCH", "PATROL"

COMMIT_BONUS = 0.10   # bonus for the action that matches the current FSM state (stops flip-flopping)


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
    chase = visible * (0.80 + 0.20 * inp["proximity"]) \
        + (1.0 - visible) * inp["recent_contact"] * 0.60

    # INVESTIGATE: louder (closer) noise and more suspicion -> higher
    investigate = 0.0
    if inp["sound"] > 0:
        investigate = 0.10 + 0.80 * inp["sound"] + 0.25 * inp["suspicion"]
    if inp["pending_investigation"]:
        investigate = max(investigate, 0.45)   # finish checking the spot
    investigate = min(investigate, 0.75)       # a visible player (>= 0.8) always wins

    # SEARCH: fresh memory of where the player was, plus suspicion
    search = inp["memory"] * (0.35 + 0.25 * inp["suspicion"])

    # PATROL: baseline, a little lower when suspicious
    patrol = 0.20 + 0.15 * (1.0 - inp["suspicion"])

    scores = {CHASE: chase, INVESTIGATE: investigate, SEARCH: search, PATROL: patrol}
    scores[current_action] += COMMIT_BONUS
    return scores


def choose_action(scores):
    """Highest score wins (ties go to the more urgent action, because of dict order)."""
    return max(scores, key=scores.get)