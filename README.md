# SkillSwap - Community Skill Exchange Platform

A ~50% working prototype of a point-based community skill exchange platform,
built for a college assignment. The core idea: instead of direct 1-to-1
barter (which breaks down when two skills take different amounts of time
or effort), everyone earns and spends a shared currency called
**Exchange Points**.

```
Person A teaches Advanced Python for 4 hours  -> earns 8 Exchange Points
Person B later spends points learning Guitar from Person C
```

This is a **prototype**, not a production system. No real money, no
production-grade auth, no cloud deployment - just enough working code to
demonstrate every required concept clearly.

---

## 1. Project Structure

```
community_skill_exchange/
    app.py                     Flask web application (routes/views)
    database.py                SQLite schema + connection helper
    models.py                  OOP classes: User, SkillOffer, SkillRequest, Exchange, Rating
    points.py                  SymPy Exchange Point calculation
    matching.py                Functional-programming matching engine (filter/map/sorted/lambda)
    multiprocessing_match.py   Multiprocessing demo (parallel matching jobs)
    socket_server.py           Plain Python socket server (Socket Programming demo)
    socket_client.py           Plain Python socket client (Socket Programming demo)
    moderator.py                Tkinter desktop app for moderators/admins
    requirements.txt
    README.md
    templates/                 Jinja2 HTML templates
    static/
        style.css
        script.js
    skill_exchange.db          Created automatically the first time you run the app
```

---

## 2. Installing Dependencies

Requires Python 3.9+ (Tkinter ships with the standard CPython installer on
Windows/Mac; on some Linux distros you may need
`sudo apt install python3-tk`).

```bash
cd community_skill_exchange
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> Note: `Flask-SocketIO` needs an async server. `eventlet` is included in
> requirements.txt for that reason. If installation of `eventlet` gives you
> trouble on Windows, you can remove it - Flask-SocketIO will fall back to
> a slower development mode, which is still fine for a prototype demo.

---

## 3. Running the Web Application

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. The SQLite database
(`skill_exchange.db`) and all tables are created automatically the first
time this runs - you do not need to run any separate setup script.

**Suggested demo flow** (matches the scenario in the assignment brief):

1. Register **Student A**. Go to *Offer a Skill* -> Skill: "Python
   Programming", Difficulty: Advanced, Duration: 4 hours, Mode: Online.
   Watch the point preview update live (4 x 2.0 = **8 points**) - this is
   SymPy running in real time via `/api/calculate-points`.
2. Open a second browser (or an incognito window) and register
   **Student B**. Go to *Request a Skill* -> same skill name, Online mode.
   You'll immediately be shown ranked matches (Student A should appear).
3. As Student B, click **Request Exchange** on Student A's card.
4. As Student A (in the other window/tab), open **My Exchanges**. If both
   tabs are open and connected, Student A gets a **live toast
   notification** ("New Skill Exchange Request received...") via
   Flask-SocketIO. Click **Accept**.
5. Mark the exchange **Completed**. Only now are the 8 points actually
   moved: Student A +8, Student B -8.
6. Both users can now leave a 1-5 star **rating** on the completed
   exchange from the *My Exchanges* page.
7. Open the **Tkinter Moderator Panel** (see below) to see the exchange,
   approve/reject skills, or change a skill's difficulty level (which
   automatically recalculates its points).

---

## 4. Running the Tkinter Moderator Panel

In a separate terminal (the web app should ideally be running too, so
they share the same `skill_exchange.db` file):

```bash
python moderator.py
```

A desktop window opens with 5 tabs: **Dashboard**, **Users**, **Skills**,
**Exchanges**, **Reports**.

- Go to the **Skills** tab to see skills submitted by users (status
  `pending`). Select one and click **Approve** to make it visible in the
  matching engine, or **Reject** to hide it.
- Select a skill, choose a new difficulty level in the dropdown (e.g.
  change Advanced -> Intermediate), and click **Apply & Recalculate
  Points** - you'll see the point value change immediately (this is the
  "moderator controls the difficulty, not the user" requirement).

---

## 5. Demonstrating Socket Programming (Client-Server)

This is a **separate, minimal** demo of the raw `socket` module,
independent of the Flask-SocketIO layer used inside the website (which
handles the *browser* real-time notifications).

**Terminal 1:**
```bash
python socket_server.py
```

**Terminal 2:**
```bash
python socket_client.py
# or with custom names:
python socket_client.py Alice Bob "Python Programming"
```

You'll see the server print the received request and send back a
notification string, and the client print the server's reply. This maps
directly to the syllabus's "Socket Programming (Client-Server)"
requirement and is easy to narrate line-by-line in a viva (see section 7).

---

## 6. Demonstrating Multiprocessing

Two ways to see it:

**A) Standalone script (simplest to show in a viva):**
```bash
python multiprocessing_match.py
```
This pulls every currently *open* skill request from the database and
matches each one in its own OS process using `multiprocessing.Pool`,
then prints the combined, ranked results.

**B) From the running website:**
Log in and visit **`/matches/parallel-demo`** (there's also a "Run
Parallel Matching Demo" button on the Dashboard). This calls the exact
same `multiprocessing_match.process_requests_in_parallel()` function
from inside a Flask route.

> Tip for the viva: create 2-3 different skill requests (e.g. Python,
> Graphic Design, Computer Repair) from different accounts first, so the
> pool has more than one job to distribute across processes.

---

## 7. Where Each College Requirement Lives (+ Viva Cheat-Sheet)

| # | Requirement | File(s) | One-line viva explanation |
|---|---|---|---|
| 1 | **Functional Programming** | `matching.py` | The matching pipeline uses `filter()` three times (skill, mode, active owner), `map()` twice (attach owner, compute score), and `sorted()` once (rank by score) - all with `lambda` functions instead of manual `for` loops. |
| 2 | **Socket Programming (Client-Server)** | `socket_server.py`, `socket_client.py` | A raw TCP server (`socket.socket`, `bind`, `listen`, `accept`) and client (`connect`, `sendall`, `recv`) exchange a plain-text "exchange request" message, independent of the web framework. |
| 3 | **Multiprocessing** | `multiprocessing_match.py` | `multiprocessing.Pool.map()` runs one matching job per open skill request in a **separate OS process**, so several requests (Python / Design / Repair) are matched concurrently instead of one after another. |
| 4 | **SymPy** | `points.py` | `Exchange Points = Duration x Difficulty Factor` is computed with `sympy.Rational` (exact fraction arithmetic), e.g. `Rational(4) * Rational(2,1) = 8`. |
| 5 | **Tkinter GUI** | `moderator.py` | A `tkinter.ttk.Notebook` desktop app with 5 tabs lets a moderator approve skills, override difficulty (auto-recalculating points), and view users/exchanges - all reading/writing the same SQLite database as the web app. |
| 6 | **Object-Oriented Programming** | `models.py` | `User`, `SkillOffer`, `SkillRequest`, `Exchange`, `Rating` are all classes with their own attributes and methods (e.g. `user.add_points()`, `exchange.set_status()`), rather than raw dicts scattered through the code. |
| 7 | **Python** | entire project | Everything (Flask backend, Tkinter GUI, sockets, matching logic) is written in plain Python 3. |
| 8 | **Web application** | `app.py`, `templates/`, `static/` | A Flask + Jinja2 + SQLite web app with registration, login, dashboard, skill offers/requests, matching, exchanges and ratings. |

---

## 8. The Point System, In Detail

```
Exchange Points = Duration (hours) x Difficulty Factor

Basic        -> factor 1.0
Intermediate -> factor 1.5
Advanced     -> factor 2.0
```

- Users **never** type in a point value themselves - `points.py`'s
  `calculate_points()` is the only place points are produced, and it's
  called automatically whenever a skill offer is created
  (`models.SkillOffer.create`) or when a moderator changes a skill's
  difficulty (`models.SkillOffer.recalculate_points`).
- Duration is restricted to **1-8 hours** (`points.MIN_DURATION` /
  `MAX_DURATION`).
- Points are only ever transferred between users when an `Exchange`'s
  status becomes `"Completed"` (`models.Exchange.set_status`) - never when
  a request is merely sent or even accepted.

---

## 9. The Matching / Recommendation System

Scoring model (out of 100), computed in `matching.score_match()`:

| Factor | Points |
|---|---|
| Skill compatibility | 40 |
| Availability overlap | 25 |
| Mode compatibility (Online/Offline/Both) | 15 |
| Location match (offline only) | 10 |
| Teacher's rating | 10 |

Pipeline (`matching.find_matches()`):

```
ALL APPROVED SKILL OFFERS
    -> filter()  same skill name
    -> filter()  compatible mode
    -> map()     attach the offer's owner (User)
    -> filter()  owner is active
    -> map()     compute compatibility score
    -> sorted()  highest score first
    -> RANKED RECOMMENDATIONS
```

The system never auto-selects a match for the user - it only displays
ranked recommendations with **View Profile** / **Request Exchange**
buttons, and the user chooses.

---

## 10. Known Simplifications (intentional - this is a 50% prototype)

- Login uses Flask sessions + `werkzeug.security` password hashing, which
  is reasonable for a prototype but not production-grade (no rate
  limiting, no email verification, no password reset flow).
- A user's point balance is allowed to go negative in this prototype
  (there's no minimum-balance check before requesting an exchange) -
  flagged here as an easy improvement to add later
  (`models.User.deduct_points`).
- The "Reports" feature has a working table and a moderator-side view/
  resolve UI, but there is no website page yet for users to *submit* a
  report - this is called out directly in the Tkinter Reports tab so it's
  not mistaken for a bug.
- Availability matching uses a simple comma-separated day-overlap check
  rather than real calendar/time-slot logic.
- No payment, Google Maps, SMS/email, or cloud deployment - all
  intentionally out of scope per the assignment brief.
