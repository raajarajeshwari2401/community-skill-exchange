"""
models.py
---------
Object-Oriented Programming layer for the platform.

College requirement demonstrated: OOP - each major entity (User,
SkillOffer, SkillRequest, Exchange, Rating) is modeled as a class with
its own attributes and behavior, instead of passing raw dictionaries
around everywhere. Each class also knows how to save/load itself from
SQLite, which keeps database.py focused only on schema/connections.
"""

from datetime import datetime
import database
import points as points_module


class User:
    """Represents a registered member of the platform."""

    def __init__(self, user_id, name, email, password, location,
                 points=0, rating=0, rating_count=0, is_active=1):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.location = location
        self.points = points
        self.rating = rating
        self.rating_count = rating_count
        self.is_active = is_active

    @staticmethod
    def create(name, email, password, location):
        """Insert a new user and return the created User object."""
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO USERS (name, email, password, location) VALUES (?, ?, ?, ?)",
            (name, email, password, location),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return User(user_id, name, email, password, location)

    @staticmethod
    def find_by_email(email):
        conn = database.get_connection()
        row = conn.execute("SELECT * FROM USERS WHERE email = ?", (email,)).fetchone()
        conn.close()
        return User.from_row(row) if row else None

    @staticmethod
    def find_by_id(user_id):
        conn = database.get_connection()
        row = conn.execute("SELECT * FROM USERS WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        return User.from_row(row) if row else None

    @staticmethod
    def all_active():
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM USERS WHERE is_active = 1").fetchall()
        conn.close()
        return [User.from_row(r) for r in rows]

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return User(
            row["user_id"], row["name"], row["email"], row["password"],
            row["location"], row["points"], row["rating"], row["rating_count"],
            row["is_active"],
        )

    def add_points(self, amount):
        """Credit this user with Exchange Points (e.g. after teaching)."""
        conn = database.get_connection()
        conn.execute("UPDATE USERS SET points = points + ? WHERE user_id = ?",
                     (amount, self.user_id))
        conn.commit()
        conn.close()
        self.points += amount

    def deduct_points(self, amount):
        """Debit this user's Exchange Points (e.g. after learning)."""
        conn = database.get_connection()
        conn.execute("UPDATE USERS SET points = points - ? WHERE user_id = ?",
                     (amount, self.user_id))
        conn.commit()
        conn.close()
        self.points -= amount

    def update_rating(self, new_rating_value):
        """Recompute the running average rating with one new review."""
        conn = database.get_connection()
        total = self.rating * self.rating_count + new_rating_value
        count = self.rating_count + 1
        avg = total / count
        conn.execute("UPDATE USERS SET rating = ?, rating_count = ? WHERE user_id = ?",
                     (avg, count, self.user_id))
        conn.commit()
        conn.close()
        self.rating, self.rating_count = avg, count

    def __repr__(self):
        return f"<User {self.user_id} {self.name}>"


class SkillOffer:
    """Represents a skill a user is willing to teach, in exchange for points."""

    def __init__(self, offer_id, user_id, skill_name, category, difficulty,
                 duration, mode, available_days, available_time, points,
                 approval_status="pending"):
        self.offer_id = offer_id
        self.user_id = user_id
        self.skill_name = skill_name
        self.category = category
        self.difficulty = difficulty
        self.duration = duration
        self.mode = mode
        self.available_days = available_days
        self.available_time = available_time
        self.points = points
        self.approval_status = approval_status

    @staticmethod
    def create(user_id, skill_name, category, difficulty, duration, mode,
               available_days, available_time):
        # Exchange Points are ALWAYS computed here via SymPy - never user input.
        calculated_points = points_module.calculate_points(float(duration), difficulty)

        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SKILL_OFFERS
            (user_id, skill_name, category, difficulty, duration, mode,
             available_days, available_time, points, approval_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (user_id, skill_name, category, difficulty, duration, mode,
              available_days, available_time, calculated_points))
        conn.commit()
        offer_id = cur.lastrowid
        conn.close()
        return SkillOffer(offer_id, user_id, skill_name, category, difficulty,
                           duration, mode, available_days, available_time,
                           calculated_points)

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return SkillOffer(
            row["offer_id"], row["user_id"], row["skill_name"], row["category"],
            row["difficulty"], row["duration"], row["mode"], row["available_days"],
            row["available_time"], row["points"], row["approval_status"],
        )

    @staticmethod
    def all_approved():
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM SKILL_OFFERS WHERE approval_status = 'approved'"
        ).fetchall()
        conn.close()
        return [SkillOffer.from_row(r) for r in rows]

    @staticmethod
    def all_for_user(user_id):
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM SKILL_OFFERS WHERE user_id = ?", (user_id,)
        ).fetchall()
        conn.close()
        return [SkillOffer.from_row(r) for r in rows]

    @staticmethod
    def all_pending():
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM SKILL_OFFERS WHERE approval_status = 'pending'"
        ).fetchall()
        conn.close()
        return [SkillOffer.from_row(r) for r in rows]

    def recalculate_points(self, new_difficulty=None):
        """Used by the moderator when they change the difficulty level."""
        difficulty = new_difficulty or self.difficulty
        new_points = points_module.calculate_points(float(self.duration), difficulty)
        conn = database.get_connection()
        conn.execute(
            "UPDATE SKILL_OFFERS SET difficulty = ?, points = ? WHERE offer_id = ?",
            (difficulty, new_points, self.offer_id),
        )
        conn.commit()
        conn.close()
        self.difficulty, self.points = difficulty, new_points
        return new_points

    def set_approval(self, status):
        conn = database.get_connection()
        conn.execute("UPDATE SKILL_OFFERS SET approval_status = ? WHERE offer_id = ?",
                     (status, self.offer_id))
        conn.commit()
        conn.close()
        self.approval_status = status

    def __repr__(self):
        return f"<SkillOffer {self.skill_name} by user {self.user_id}>"


class SkillRequest:
    """Represents a skill a user wants to learn."""

    def __init__(self, request_id, user_id, skill_name, category, duration,
                 mode, location, available_days, available_time, status="open"):
        self.request_id = request_id
        self.user_id = user_id
        self.skill_name = skill_name
        self.category = category
        self.duration = duration
        self.mode = mode
        self.location = location
        self.available_days = available_days
        self.available_time = available_time
        self.status = status

    @staticmethod
    def create(user_id, skill_name, category, duration, mode, location,
               available_days, available_time):
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SKILL_REQUESTS
            (user_id, skill_name, category, duration, mode, location,
             available_days, available_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (user_id, skill_name, category, duration, mode, location,
              available_days, available_time))
        conn.commit()
        request_id = cur.lastrowid
        conn.close()
        return SkillRequest(request_id, user_id, skill_name, category, duration,
                             mode, location, available_days, available_time)

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return SkillRequest(
            row["request_id"], row["user_id"], row["skill_name"], row["category"],
            row["duration"], row["mode"], row["location"], row["available_days"],
            row["available_time"], row["status"],
        )

    @staticmethod
    def all_open():
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM SKILL_REQUESTS WHERE status = 'open'").fetchall()
        conn.close()
        return [SkillRequest.from_row(r) for r in rows]

    @staticmethod
    def all_for_user(user_id):
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM SKILL_REQUESTS WHERE user_id = ? ORDER BY request_id DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return [SkillRequest.from_row(r) for r in rows]

    def __repr__(self):
        return f"<SkillRequest {self.skill_name} by user {self.user_id}>"


class Exchange:
    """Represents an agreed skill exchange between two users."""

    def __init__(self, exchange_id, requester_id, provider_id, offer_id, skill,
                 duration, points, status="Pending", created_at=None, completed_at=None):
        self.exchange_id = exchange_id
        self.requester_id = requester_id
        self.provider_id = provider_id
        self.offer_id = offer_id
        self.skill = skill
        self.duration = duration
        self.points = points
        self.status = status
        self.created_at = created_at
        self.completed_at = completed_at

    @staticmethod
    def create(requester_id, provider_id, offer_id, skill, duration, points):
        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO EXCHANGES
            (requester_id, provider_id, offer_id, skill, duration, points, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (requester_id, provider_id, offer_id, skill, duration, points))
        conn.commit()
        exchange_id = cur.lastrowid
        conn.close()
        return Exchange(exchange_id, requester_id, provider_id, offer_id, skill,
                         duration, points)

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return Exchange(
            row["exchange_id"], row["requester_id"], row["provider_id"],
            row["offer_id"], row["skill"], row["duration"], row["points"],
            row["status"], row["created_at"], row["completed_at"],
        )

    @staticmethod
    def find_by_id(exchange_id):
        conn = database.get_connection()
        row = conn.execute("SELECT * FROM EXCHANGES WHERE exchange_id = ?",
                            (exchange_id,)).fetchone()
        conn.close()
        return Exchange.from_row(row)

    @staticmethod
    def all_for_user(user_id):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT * FROM EXCHANGES
            WHERE requester_id = ? OR provider_id = ?
            ORDER BY exchange_id DESC
        """, (user_id, user_id)).fetchall()
        conn.close()
        return [Exchange.from_row(r) for r in rows]

    @staticmethod
    def all():
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM EXCHANGES ORDER BY exchange_id DESC").fetchall()
        conn.close()
        return [Exchange.from_row(r) for r in rows]

    def set_status(self, status):
        """
        Move the exchange through its lifecycle:
        Pending -> Accepted -> Completed  (or -> Rejected)
        Points are ONLY transferred here, and ONLY on Completed.
        """
        conn = database.get_connection()
        if status == "Completed":
            conn.execute(
                "UPDATE EXCHANGES SET status = ?, completed_at = ? WHERE exchange_id = ?",
                (status, datetime.now().isoformat(timespec="seconds"), self.exchange_id),
            )
        else:
            conn.execute("UPDATE EXCHANGES SET status = ? WHERE exchange_id = ?",
                         (status, self.exchange_id))
        conn.commit()
        conn.close()
        self.status = status

        if status == "Completed":
            # Provider (the teacher) earns points, requester (the learner) spends them.
            provider = User.find_by_id(self.provider_id)
            requester = User.find_by_id(self.requester_id)
            if provider:
                provider.add_points(self.points)
            if requester:
                requester.deduct_points(self.points)

    def __repr__(self):
        return f"<Exchange {self.exchange_id} {self.skill} [{self.status}]>"


class Rating:
    """Represents a 1-5 star review left after a completed exchange."""

    def __init__(self, rating_id, exchange_id, reviewer_id, reviewed_user_id,
                 rating, feedback=None):
        self.rating_id = rating_id
        self.exchange_id = exchange_id
        self.reviewer_id = reviewer_id
        self.reviewed_user_id = reviewed_user_id
        self.rating = rating
        self.feedback = feedback

    @staticmethod
    def create(exchange_id, reviewer_id, reviewed_user_id, rating_value, feedback=""):
        exchange = Exchange.find_by_id(exchange_id)
        if not exchange or exchange.status != "Completed":
            raise ValueError("Ratings are only allowed after a Completed exchange.")

        conn = database.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO RATINGS (exchange_id, reviewer_id, reviewed_user_id, rating, feedback)
            VALUES (?, ?, ?, ?, ?)
        """, (exchange_id, reviewer_id, reviewed_user_id, rating_value, feedback))
        conn.commit()
        rating_id = cur.lastrowid
        conn.close()

        reviewed_user = User.find_by_id(reviewed_user_id)
        if reviewed_user:
            reviewed_user.update_rating(rating_value)

        return Rating(rating_id, exchange_id, reviewer_id, reviewed_user_id,
                       rating_value, feedback)

    @staticmethod
    def exists_for(exchange_id, reviewer_id):
        conn = database.get_connection()
        row = conn.execute(
            "SELECT * FROM RATINGS WHERE exchange_id = ? AND reviewer_id = ?",
            (exchange_id, reviewer_id),
        ).fetchone()
        conn.close()
        return row is not None

    def __repr__(self):
        return f"<Rating {self.rating}* for user {self.reviewed_user_id}>"
