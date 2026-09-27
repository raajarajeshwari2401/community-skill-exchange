"""
multiprocessing_match.py
------------------------
College requirement demonstrated: MULTIPROCESSING.

Important distinction to remember for the viva:
    - matching.py's filter()/map()/sorted() = HOW one matching job
      processes its list of candidate offers (functional programming).
    - multiprocessing_match.py = HOW MANY matching jobs (one per open
      skill request) run AT THE SAME TIME, in separate OS processes.

Scenario from the spec:
    Request 1 -> Python
    Request 2 -> Graphic Design
    Request 3 -> Computer Repair

Each of those requests is independent, so instead of matching them one
after another in a loop, we hand each request to its own process using
multiprocessing.Pool. The main process then simply combines the results.

Each worker process opens its OWN sqlite3 connection (SQLite connections
cannot be shared/pickled across processes), does its filter/map/sorted
work via matching.find_matches(), and returns the ranked list.
"""

from multiprocessing import Pool, cpu_count
import database
import models
import matching


def _match_single_request(request_row_dict):
    """
    Worker function executed inside a SEPARATE PROCESS.
    Must be a top-level function (not a lambda/method) so it can be pickled.
    """
    # Each process needs its own DB connection / offer list.
    conn = database.get_connection()
    offers_rows = conn.execute(
        "SELECT * FROM SKILL_OFFERS WHERE approval_status = 'approved'"
    ).fetchall()
    conn.close()

    all_offers = [models.SkillOffer.from_row(r) for r in offers_rows]

    ranked = matching.find_matches(
        request_row_dict,
        all_offers=all_offers,
        exclude_user_id=request_row_dict.get("user_id"),
    )

    # Convert to lightweight, picklable summaries (avoid returning live
    # sqlite-backed objects across the process boundary).
    summary = [
        {
            "offer_id": item["offer"].offer_id,
            "owner_name": item["owner"].name,
            "skill_name": item["offer"].skill_name,
            "points": item["offer"].points,
            "total_score": item["score"]["total"],
        }
        for item in ranked
    ]

    return {
        "request_id": request_row_dict["request_id"],
        "skill_name": request_row_dict["skill_name"],
        "matches": summary,
    }


def process_requests_in_parallel(request_dicts, max_workers=4):
    """
    Run matching for MULTIPLE skill requests concurrently using a process pool.

    Args:
        request_dicts: list of dicts, each shaped like a SKILL_REQUESTS row.
        max_workers: cap on how many OS processes to spawn.

    Returns:
        dict: {request_id: {"skill_name":..., "matches":[...]}}
    """
    if not request_dicts:
        return {}

    workers = min(max_workers, cpu_count(), len(request_dicts))
    with Pool(processes=max(workers, 1)) as pool:
        results = pool.map(_match_single_request, request_dicts)

    return {r["request_id"]: r for r in results}


def demo():
    """
    Standalone demo you can run directly:
        python multiprocessing_match.py
    Pulls all currently OPEN requests from the DB and matches them in parallel.
    """
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM SKILL_REQUESTS WHERE status = 'open'").fetchall()
    conn.close()

    request_dicts = [dict(r) for r in rows]
    if not request_dicts:
        print("No open skill requests found. Create some via the website first.")
        return

    print(f"Matching {len(request_dicts)} open request(s) in parallel processes...")
    results = process_requests_in_parallel(request_dicts)

    for request_id, info in results.items():
        print(f"\nRequest #{request_id} ({info['skill_name']}):")
        if not info["matches"]:
            print("  No compatible offers found.")
        for m in info["matches"]:
            print(f"  - {m['owner_name']} | {m['skill_name']} | "
                  f"{m['points']} pts | score {m['total_score']}")


if __name__ == "__main__":
    demo()
