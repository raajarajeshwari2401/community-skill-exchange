"""
matching.py
-----------
The recommendation / matching engine.

College requirement demonstrated: FUNCTIONAL PROGRAMMING
(filter, map, sorted, lambda) used meaningfully to turn a big list of
skill offers into a small, ranked list of recommendations.

Conceptual pipeline (this is the exact flow to describe in a viva):

    ALL SKILL OFFERS
        |
        v  filter() -> same skill name & approved by moderator
        |
        v  filter() -> compatible mode (Online/Offline/Both)
        |
        v  filter() -> compatible availability (days overlap)
        |
        v  map()    -> compute a compatibility score dict for each offer
        |
        v  sorted() -> rank candidates, highest score first
        |
        v
    RANKED RECOMMENDATIONS (shown on matches.html)

Scoring model (out of 100):
    Skill compatibility = 40
    Availability         = 25
    Mode                 = 15
    Location             = 10
    Rating               = 10
"""

import models


# ---------------------------------------------------------------------------
# Small helper predicates (kept as plain functions so they can be reused
# both stand-alone and inside lambda-based filter/map calls below).
# ---------------------------------------------------------------------------

def _mode_compatible(offer_mode, wanted_mode):
    if offer_mode == "Both" or wanted_mode == "Both":
        return True
    return offer_mode == wanted_mode


def _availability_overlap(offer_days, wanted_days):
    """Simple overlap check between two comma-separated day strings."""
    if not offer_days or not wanted_days:
        return False
    offer_set = set(d.strip().lower() for d in offer_days.split(","))
    wanted_set = set(d.strip().lower() for d in wanted_days.split(","))
    return len(offer_set & wanted_set) > 0


def _location_match(offer_user_location, wanted_location, mode):
    """Location only matters for Offline exchanges."""
    if mode == "Online":
        return True  # location is irrelevant online -> full marks
    if not offer_user_location or not wanted_location:
        return False
    return offer_user_location.strip().lower() == wanted_location.strip().lower()


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_match(offer, offer_owner, request_dict):
    """
    Build the 100-point compatibility breakdown for one (offer, request) pair.
    Returns a dict so the template can show the same breakdown the spec asks for.
    """
    skill_score = 40 if offer.skill_name.strip().lower() == request_dict["skill_name"].strip().lower() else 0

    availability_score = 25 if _availability_overlap(
        offer.available_days, request_dict.get("available_days", "")
    ) else 0

    mode_score = 15 if _mode_compatible(offer.mode, request_dict["mode"]) else 0

    location_score = 10 if _location_match(
        offer_owner.location, request_dict.get("location", ""), request_dict["mode"]
    ) else 0

    # Rating out of 10 (rating is stored 0-5 stars -> scale to /10)
    rating_score = round((offer_owner.rating or 0) / 5 * 10, 1)

    total = skill_score + availability_score + mode_score + location_score + rating_score

    return {
        "skill_score": skill_score,
        "availability_score": availability_score,
        "mode_score": mode_score,
        "location_score": location_score,
        "rating_score": rating_score,
        "total": round(total, 1),
    }


# ---------------------------------------------------------------------------
# The main functional-programming pipeline
# ---------------------------------------------------------------------------

def find_matches(request_dict, all_offers=None, exclude_user_id=None):
    """
    Given a skill request (as a dict with skill_name/mode/location/etc.),
    return a ranked list of candidate matches.

    Each item in the returned list is:
        {"offer": SkillOffer, "owner": User, "score": {...}}
    """
    if all_offers is None:
        all_offers = models.SkillOffer.all_approved()

    # STEP 1 - filter(): keep only offers that teach the requested skill
    same_skill = list(filter(
        lambda o: o.skill_name.strip().lower() == request_dict["skill_name"].strip().lower(),
        all_offers,
    ))

    # STEP 2 - filter(): keep only offers with a compatible mode
    mode_ok = list(filter(
        lambda o: _mode_compatible(o.mode, request_dict["mode"]),
        same_skill,
    ))

    # Don't recommend the requester's own offers
    if exclude_user_id is not None:
        mode_ok = list(filter(lambda o: o.user_id != exclude_user_id, mode_ok))

    # STEP 3 - map(): attach the offer's owner (User) so we can score rating/location
    with_owner = list(map(lambda o: (o, models.User.find_by_id(o.user_id)), mode_ok))
    with_owner = list(filter(lambda pair: pair[1] is not None and pair[1].is_active, with_owner))

    # STEP 4 - map(): compute the compatibility score for every remaining candidate
    scored = list(map(
        lambda pair: {"offer": pair[0], "owner": pair[1],
                       "score": score_match(pair[0], pair[1], request_dict)},
        with_owner,
    ))

    # STEP 5 - sorted(): rank by total compatibility score, highest first
    ranked = sorted(scored, key=lambda item: item["score"]["total"], reverse=True)

    return ranked


def quick_point_estimate(offer):
    """Used on the Request Skill page to preview the point cost of an offer."""
    return offer.points
