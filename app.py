from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Home route - Admin dashboard
@app.route("/", methods=["GET", "POST"])
def dashboard():
    with sqlite3.connect("complaints.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM complaints")
        complaints = cur.fetchall()

        # Counts for dashboard summary
        total = len(complaints)
        unassigned = sum(1 for c in complaints if c[5] == "Unassigned")
        in_progress = sum(1 for c in complaints if c[5] == "In Progress")
        completed = sum(1 for c in complaints if c[5] == "Completed")

    return render_template("dashboard.html", complaints=complaints,
                           total=total, unassigned=unassigned,
                           in_progress=in_progress, completed=completed)

# Complaint status update
@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    status = request.form["status"]
    assigned = request.form["assigned"]
    comment = request.form["comment"]

    with sqlite3.connect("complaints.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE complaints
            SET status=?, assigned=?, comment=?
            WHERE id=?
        """, (status, assigned, comment, id))
        conn.commit()

    return redirect(url_for("dashboard"))

# Track complaint for customer
@app.route("/track", methods=["GET", "POST"])
def track():
    complaints = []
    searched = False
    if request.method == "POST":
        mobile = request.form["mobile"].strip()
        searched = True
        if mobile.isdigit() and len(mobile) == 10:
            with sqlite3.connect("complaints.db") as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM complaints WHERE mobile=?", (mobile,))
                complaints = cur.fetchall()
    return render_template("track.html", complaints=complaints, searched=searched)

# Complaint submission (optional route if using a public form)
@app.route("/submit", methods=["POST"])
def submit_complaint():
    name = request.form["name"]
    issue = request.form["issue"]
    mobile = request.form["mobile"]
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect("complaints.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO complaints (name, issue, mobile, date, status, assigned, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, issue, mobile, date, "Unassigned", "", ""))
        conn.commit()

    return redirect(url_for("track"))

if __name__ == "__main__":
    app.run(debug=True)
