"""
moderator.py
------------
College requirement demonstrated: TKINTER GUI (separate desktop app for
moderators/admins). The main user-facing product stays a web app (Flask);
this is the internal tool for the platform's moderators.

Run with:
    python moderator.py

Tabs:
    Dashboard  - platform-wide counts
    Users      - view users, deactivate misbehaving accounts
    Skills     - approve/reject skill offers, change difficulty
                 (recalculates Exchange Points automatically via SymPy)
    Exchanges  - read-only view of every exchange and its status
    Reports    - view/resolve simple user reports
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database
import models

database.init_db()  # make sure tables exist even if run before app.py


class ModeratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SkillSwap - Moderator Panel")
        self.geometry("980x600")
        self.configure(bg="#f7f8f5")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.dashboard_tab = DashboardTab(notebook)
        self.users_tab = UsersTab(notebook)
        self.skills_tab = SkillsTab(notebook)
        self.exchanges_tab = ExchangesTab(notebook)
        self.reports_tab = ReportsTab(notebook)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.users_tab, text="Users")
        notebook.add(self.skills_tab, text="Skills")
        notebook.add(self.exchanges_tab, text="Exchanges")
        notebook.add(self.reports_tab, text="Reports")


# ---------------------------------------------------------------------------
# Dashboard tab
# ---------------------------------------------------------------------------

class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.stat_labels = {}

        title = ttk.Label(self, text="Platform Overview", font=("Segoe UI", 16, "bold"))
        title.pack(pady=(20, 10))

        grid = ttk.Frame(self)
        grid.pack(pady=10)

        stats = ["Users", "Skill Offers", "Skill Requests", "Exchanges", "Average Rating"]
        for i, stat in enumerate(stats):
            box = ttk.Frame(grid, relief="groove", padding=20)
            box.grid(row=0, column=i, padx=10)
            value_label = ttk.Label(box, text="0", font=("Segoe UI", 20, "bold"))
            value_label.pack()
            ttk.Label(box, text=stat).pack()
            self.stat_labels[stat] = value_label

        ttk.Button(self, text="Refresh", command=self.refresh).pack(pady=20)
        self.refresh()

    def refresh(self):
        conn = database.get_connection()
        user_count = conn.execute("SELECT COUNT(*) c FROM USERS").fetchone()["c"]
        offer_count = conn.execute("SELECT COUNT(*) c FROM SKILL_OFFERS").fetchone()["c"]
        request_count = conn.execute("SELECT COUNT(*) c FROM SKILL_REQUESTS").fetchone()["c"]
        exchange_count = conn.execute("SELECT COUNT(*) c FROM EXCHANGES").fetchone()["c"]
        avg_rating = conn.execute("SELECT AVG(rating) a FROM USERS WHERE rating > 0").fetchone()["a"]
        conn.close()

        self.stat_labels["Users"].config(text=str(user_count))
        self.stat_labels["Skill Offers"].config(text=str(offer_count))
        self.stat_labels["Skill Requests"].config(text=str(request_count))
        self.stat_labels["Exchanges"].config(text=str(exchange_count))
        self.stat_labels["Average Rating"].config(
            text=f"{avg_rating:.1f}" if avg_rating else "N/A"
        )


# ---------------------------------------------------------------------------
# Users tab
# ---------------------------------------------------------------------------

class UsersTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        columns = ("id", "name", "location", "points", "rating", "active")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        for col, label in zip(columns, ["ID", "Name", "Location", "Points", "Rating", "Active"]):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=5)
        ttk.Button(btn_row, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        ttk.Button(btn_row, text="Deactivate Selected User", command=self.deactivate).pack(side="left", padx=5)

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM USERS ORDER BY user_id").fetchall()
        conn.close()
        for r in rows:
            self.tree.insert("", "end", iid=r["user_id"], values=(
                r["user_id"], r["name"], r["location"], r["points"],
                round(r["rating"], 1), "Yes" if r["is_active"] else "No",
            ))

    def deactivate(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a user first.")
            return
        user_id = int(selected[0])
        conn = database.get_connection()
        conn.execute("UPDATE USERS SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Done", f"User #{user_id} deactivated.")
        self.refresh()


# ---------------------------------------------------------------------------
# Skills tab (approval + difficulty override -> automatic point recalculation)
# ---------------------------------------------------------------------------

class SkillsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        columns = ("id", "user", "skill", "difficulty", "duration", "points", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        headers = ["ID", "User ID", "Skill", "Difficulty", "Duration (h)", "Points", "Status"]
        for col, label in zip(columns, headers):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        control_row = ttk.Frame(self)
        control_row.pack(pady=5)

        ttk.Button(control_row, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        ttk.Button(control_row, text="Approve", command=self.approve).pack(side="left", padx=5)
        ttk.Button(control_row, text="Reject", command=self.reject).pack(side="left", padx=5)

        ttk.Label(control_row, text="Change Level to:").pack(side="left", padx=(20, 5))
        self.level_var = tk.StringVar(value="Intermediate")
        ttk.Combobox(control_row, textvariable=self.level_var,
                     values=["Basic", "Intermediate", "Advanced"], width=12,
                     state="readonly").pack(side="left")
        ttk.Button(control_row, text="Apply & Recalculate Points",
                   command=self.change_level).pack(side="left", padx=5)

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM SKILL_OFFERS ORDER BY offer_id DESC").fetchall()
        conn.close()
        for r in rows:
            self.tree.insert("", "end", iid=r["offer_id"], values=(
                r["offer_id"], r["user_id"], r["skill_name"], r["difficulty"],
                r["duration"], r["points"], r["approval_status"],
            ))

    def _get_selected_offer(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a skill offer first.")
            return None
        offer_id = int(selected[0])
        conn = database.get_connection()
        row = conn.execute("SELECT * FROM SKILL_OFFERS WHERE offer_id = ?",
                            (offer_id,)).fetchone()
        conn.close()
        return models.SkillOffer.from_row(row)

    def approve(self):
        offer = self._get_selected_offer()
        if offer:
            offer.set_approval("approved")
            messagebox.showinfo("Approved", f"'{offer.skill_name}' approved.")
            self.refresh()

    def reject(self):
        offer = self._get_selected_offer()
        if offer:
            offer.set_approval("rejected")
            messagebox.showinfo("Rejected", f"'{offer.skill_name}' rejected.")
            self.refresh()

    def change_level(self):
        offer = self._get_selected_offer()
        if offer:
            new_points = offer.recalculate_points(self.level_var.get())
            messagebox.showinfo(
                "Recalculated",
                f"'{offer.skill_name}' is now {offer.difficulty}. "
                f"New Exchange Points (via SymPy): {new_points}",
            )
            self.refresh()


# ---------------------------------------------------------------------------
# Exchanges tab (read-only overview)
# ---------------------------------------------------------------------------

class ExchangesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        columns = ("id", "requester", "provider", "skill", "points", "status", "created")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        headers = ["ID", "Requester ID", "Provider ID", "Skill", "Points", "Status", "Created At"]
        for col, label in zip(columns, headers):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(self, text="Refresh", command=self.refresh).pack(pady=5)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM EXCHANGES ORDER BY exchange_id DESC").fetchall()
        conn.close()
        for r in rows:
            self.tree.insert("", "end", iid=r["exchange_id"], values=(
                r["exchange_id"], r["requester_id"], r["provider_id"], r["skill"],
                r["points"], r["status"], r["created_at"],
            ))


# ---------------------------------------------------------------------------
# Reports tab
# ---------------------------------------------------------------------------

class ReportsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        columns = ("id", "reported_user", "reporter", "reason", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        headers = ["ID", "Reported User ID", "Reporter ID", "Reason", "Status"]
        for col, label in zip(columns, headers):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=5)
        ttk.Button(btn_row, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        ttk.Button(btn_row, text="Resolve Selected", command=self.resolve).pack(side="left", padx=5)

        note = ttk.Label(
            self,
            text="(Prototype note: reports are not yet submittable from the website; "
                 "this tab is ready for that feature to be added later.)",
            foreground="#6c7a75",
        )
        note.pack(pady=5)

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = database.get_connection()
        rows = conn.execute("SELECT * FROM REPORTS ORDER BY report_id DESC").fetchall()
        conn.close()
        for r in rows:
            self.tree.insert("", "end", iid=r["report_id"], values=(
                r["report_id"], r["reported_user_id"], r["reporter_id"],
                r["reason"], r["status"],
            ))

    def resolve(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No selection", "Please select a report first.")
            return
        report_id = int(selected[0])
        conn = database.get_connection()
        conn.execute("UPDATE REPORTS SET status = 'resolved' WHERE report_id = ?", (report_id,))
        conn.commit()
        conn.close()
        self.refresh()


if __name__ == "__main__":
    app = ModeratorApp()
    app.mainloop()
