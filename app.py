"""
app.py
------
Main Flask web application for SkillSwap (Community Skill Exchange Platform).

Wires together:
  - database.py        (SQLite schema / connections)
  - models.py           (OOP entities: User, SkillOffer, SkillRequest, Exchange, Rating)
  - points.py           (SymPy Exchange Point calculation)
  - matching.py         (functional-programming matching engine)
  - multiprocessing_match.py (parallel matching demo, triggered from the UI)
  - Flask-SocketIO      (real-time browser notifications)

Kept deliberately simple for a 50% college prototype: session-based login
(no password hashing complexity beyond a basic hash), server-rendered
Jinja2 templates, and small route handlers that mostly just call into
models.py.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, emit
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

import database
import models
import points as points_module
import matching
import multiprocessing_match

app = Flask(__name__)
app.secret_key = "skillswap-prototype-secret-key"  # fine for a college prototype

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Make sure tables exist before the first request is handled.
database.init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view_func):
    """Simple decorator: redirect to /login if no user is in the session."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    return models.User.find_by_id(user_id) if user_id else None


def notify(user_id, message):
    """
    Store a notification in SQLite AND push it live over Flask-SocketIO
    to that user's private room (if they currently have the page open).
    """
    conn = database.get_connection()
    conn.execute(
        "INSERT INTO NOTIFICATIONS (user_id, message) VALUES (?, ?)",
        (user_id, message),
    )
    conn.commit()
    conn.close()
    socketio.emit("notification", {"message": message}, room=f"user_{user_id}")


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html", user=current_user())


@app.route("/explore")
@login_required
def explore():
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT * FROM SKILL_OFFERS "
        "WHERE approval_status = 'Approved' "
        "ORDER BY offer_id DESC"
    ).fetchall()
    conn.close()

    return render_template(
        "explore.html",
        user=current_user(),
        offers=rows
    )


@app.route("/how-it-works")
def how_it_works():
    return render_template("index.html", user=current_user(), scroll_to="how-it-works")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        location = request.form.get("location", "").strip()

        if models.User.find_by_email(email):
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        user = models.User.create(name, email, hashed, location)
        session["user_id"] = user.user_id
        flash("Welcome to SkillSwap! Your account was created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = models.User.find_by_email(email)
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.user_id
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Profile / Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    my_offers = models.SkillOffer.all_for_user(user.user_id)
    my_requests = models.SkillRequest.all_for_user(user.user_id)
    my_exchanges = models.Exchange.all_for_user(user.user_id)

    pending = [e for e in my_exchanges if e.status == "Pending"]
    active = [e for e in my_exchanges if e.status == "Accepted"]
    history = [e for e in my_exchanges if e.status in ("Completed", "Rejected")]

    # Recommended matches: build from this user's most recent open request, if any.
    recommended = []
    active_request = my_requests[0] if my_requests else None
    if active_request and active_request.status == "open":
        req_dict = {
            "skill_name": active_request.skill_name,
            "mode": active_request.mode,
            "location": active_request.location,
            "available_days": active_request.available_days,
        }
        recommended = matching.find_matches(req_dict, exclude_user_id=user.user_id)[:5]

    return render_template(
        "dashboard.html",
        user=user,
        my_offers=my_offers,
        my_requests=my_requests,
        pending=pending,
        active=active,
        history=history,
        recommended=recommended,
        active_request=active_request,
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()

    if request.method == "POST":
        name = request.form["name"].strip()
        location = request.form.get("location", "").strip()
        conn = database.get_connection()
        conn.execute("UPDATE USERS SET name = ?, location = ? WHERE user_id = ?",
                     (name, location, user.user_id))
        conn.commit()
        conn.close()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    my_offers = models.SkillOffer.all_for_user(user.user_id)
    my_requests = models.SkillRequest.all_for_user(user.user_id)
    return render_template("profile.html", user=user, my_offers=my_offers,
                            my_requests=my_requests)


# ---------------------------------------------------------------------------
# Offer a Skill  (SymPy point calculation happens inside models.SkillOffer.create)
# ---------------------------------------------------------------------------

@app.route("/offer-skill", methods=["GET", "POST"])
@login_required
def offer_skill():
    user = current_user()

    if request.method == "POST":
        skill_name = request.form["skill_name"].strip()
        category = request.form.get("category", "").strip()
        difficulty = request.form["difficulty"]
        duration = float(request.form["duration"])
        mode = request.form["mode"]
        available_days = ",".join(request.form.getlist("available_days"))
        available_time = request.form.get("available_time", "").strip()

        try:
            offer = models.SkillOffer.create(
                user.user_id, skill_name, category, difficulty, duration, mode,
                available_days, available_time,
            )
            flash(
                f"Skill submitted for moderator approval. "
                f"Calculated Exchange Points: {offer.points}", "success"
            )
        except ValueError as e:
            flash(str(e), "error")

        return redirect(url_for("dashboard"))

    return render_template("offer_skill.html", user=user)


@app.route("/api/calculate-points")
@login_required
def api_calculate_points():
    """AJAX helper so the Offer Skill form can preview points live via SymPy."""
    duration = float(request.args.get("duration", 0))
    difficulty = request.args.get("difficulty", "Basic")
    try:
        pts = points_module.calculate_points(duration, difficulty)
        return jsonify({"points": pts, "ok": True})
    except ValueError as e:
        return jsonify({"error": str(e), "ok": False})


# ---------------------------------------------------------------------------
# Request a Skill
# ---------------------------------------------------------------------------

@app.route("/request-skill", methods=["GET", "POST"])
@login_required
def request_skill():
    user = current_user()

    if request.method == "POST":
        skill_name = request.form["skill_name"].strip()
        category = request.form.get("category", "").strip()
        duration = float(request.form["duration"])
        mode = request.form["mode"]
        location = request.form.get("location", "").strip()
        available_days = ",".join(request.form.getlist("available_days"))
        available_time = request.form.get("available_time", "").strip()

        skill_request = models.SkillRequest.create(
            user.user_id, skill_name, category, duration, mode, location,
            available_days, available_time,
        )
        flash("Request created. Here are your matches!", "success")
        return redirect(url_for("view_matches", request_id=skill_request.request_id))

    return render_template("request_skill.html", user=user)


@app.route("/matches/<int:request_id>")
@login_required
def view_matches(request_id):
    user = current_user()
    conn = database.get_connection()
    row = conn.execute("SELECT * FROM SKILL_REQUESTS WHERE request_id = ?",
                        (request_id,)).fetchone()
    conn.close()
    if row is None:
        flash("Request not found.", "error")
        return redirect(url_for("dashboard"))

    skill_request = models.SkillRequest.from_row(row)
    req_dict = {
        "skill_name": skill_request.skill_name,
        "mode": skill_request.mode,
        "location": skill_request.location,
        "available_days": skill_request.available_days,
    }
    ranked = matching.find_matches(req_dict, exclude_user_id=user.user_id)

    return render_template("matches.html", user=user, skill_request=skill_request,
                            ranked=ranked)


@app.route("/matches/parallel-demo")
@login_required
def parallel_match_demo():
    """
    Demonstrates the MULTIPROCESSING requirement directly from the browser:
    matches every currently open skill request in parallel worker processes
    and shows the combined results.
    """
    conn = database.get_connection()
    rows = conn.execute("SELECT * FROM SKILL_REQUESTS WHERE status = 'open'").fetchall()
    conn.close()

    request_dicts = [dict(r) for r in rows]
    results = multiprocessing_match.process_requests_in_parallel(request_dicts)

    return render_template("matches.html", user=current_user(), parallel_results=results,
                            skill_request=None, ranked=None)


# ---------------------------------------------------------------------------
# Exchanges: request / accept / reject / complete / rate
# ---------------------------------------------------------------------------

@app.route("/exchanges")
@login_required
def exchanges():
    user = current_user()
    my_exchanges = models.Exchange.all_for_user(user.user_id)
    # Attach display names + "am I the provider?" flag for the template
    enriched = []
    for e in my_exchanges:
        requester = models.User.find_by_id(e.requester_id)
        provider = models.User.find_by_id(e.provider_id)
        enriched.append({
            "exchange": e,
            "requester": requester,
            "provider": provider,
            "is_provider": e.provider_id == user.user_id,
            "already_rated": models.Rating.exists_for(e.exchange_id, user.user_id),
        })
    return render_template("exchanges.html", user=user, enriched=enriched)


@app.route("/exchanges/request/<int:offer_id>", methods=["POST"])
@login_required
def create_exchange_request(offer_id):
    user = current_user()
    conn = database.get_connection()
    row = conn.execute("SELECT * FROM SKILL_OFFERS WHERE offer_id = ?",
                        (offer_id,)).fetchone()
    conn.close()

    if row is None:
        flash("Skill offer not found.", "error")
        return redirect(url_for("dashboard"))

    offer = models.SkillOffer.from_row(row)
    if offer.user_id == user.user_id:
        flash("You can't request your own skill offer.", "error")
        return redirect(url_for("dashboard"))

    exchange = models.Exchange.create(
        requester_id=user.user_id,
        provider_id=offer.user_id,
        offer_id=offer.offer_id,
        skill=offer.skill_name,
        duration=offer.duration,
        points=offer.points,
    )

    notify(offer.user_id,
           f"New Skill Exchange Request received from {user.name} for '{offer.skill_name}'.")

    flash("Exchange request sent!", "success")
    return redirect(url_for("exchanges"))


@app.route("/exchanges/<int:exchange_id>/accept", methods=["POST"])
@login_required
def accept_exchange(exchange_id):
    return _update_exchange_status(exchange_id, "Accepted")


@app.route("/exchanges/<int:exchange_id>/reject", methods=["POST"])
@login_required
def reject_exchange(exchange_id):
    return _update_exchange_status(exchange_id, "Rejected")


@app.route("/exchanges/<int:exchange_id>/complete", methods=["POST"])
@login_required
def complete_exchange(exchange_id):
    return _update_exchange_status(exchange_id, "Completed")


def _update_exchange_status(exchange_id, new_status):
    user = current_user()
    exchange = models.Exchange.find_by_id(exchange_id)
    if exchange is None:
        flash("Exchange not found.", "error")
        return redirect(url_for("exchanges"))

    if user.user_id not in (exchange.requester_id, exchange.provider_id):
        flash("You are not part of this exchange.", "error")
        return redirect(url_for("exchanges"))

    exchange.set_status(new_status)

    other_user_id = (exchange.requester_id if user.user_id == exchange.provider_id
                     else exchange.provider_id)

    messages = {
        "Accepted": "Your Skill Exchange Request was accepted.",
        "Rejected": "Your Skill Exchange Request was declined.",
        "Completed": f"Your exchange for '{exchange.skill}' is now marked Completed. "
                     f"{exchange.points} Exchange Points have been transferred.",
    }
    notify(other_user_id, messages.get(new_status, f"Exchange status updated to {new_status}."))

    flash(f"Exchange marked as {new_status}.", "success")
    return redirect(url_for("exchanges"))


@app.route("/exchanges/<int:exchange_id>/rate", methods=["POST"])
@login_required
def rate_exchange(exchange_id):
    user = current_user()
    exchange = models.Exchange.find_by_id(exchange_id)
    if exchange is None or exchange.status != "Completed":
        flash("You can only rate completed exchanges.", "error")
        return redirect(url_for("exchanges"))

    if models.Rating.exists_for(exchange_id, user.user_id):
        flash("You already rated this exchange.", "error")
        return redirect(url_for("exchanges"))

    reviewed_user_id = (exchange.requester_id if user.user_id == exchange.provider_id
                         else exchange.provider_id)

    rating_value = int(request.form["rating"])
    feedback = request.form.get("feedback", "").strip()

    models.Rating.create(exchange_id, user.user_id, reviewed_user_id, rating_value, feedback)
    flash("Thanks for your feedback!", "success")
    return redirect(url_for("exchanges"))


# ---------------------------------------------------------------------------
# Notifications (polling fallback + SocketIO room join)
# ---------------------------------------------------------------------------

@app.route("/api/notifications")
@login_required
def api_notifications():
    user = current_user()
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT * FROM NOTIFICATIONS WHERE user_id = ? ORDER BY notification_id DESC LIMIT 10",
        (user.user_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@socketio.on("join")
def handle_join(data):
    """Browser tells the server which user's room to join after page load."""
    user_id = data.get("user_id")
    if user_id:
        join_room(f"user_{user_id}")


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
