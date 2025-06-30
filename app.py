from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'database.db'

# ✅ Ensure complaints table is created
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                mobile TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Unassigned',
                remarks TEXT
            )
        ''')
        conn.commit()

# ✅ Immediately initialize DB at import time
init_db()


@app.route('/')
def dashboard():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM complaints")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Unassigned'")
    unassigned = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
    in_progress = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Completed'")
    completed = c.fetchone()[0]

    c.execute("SELECT * FROM complaints ORDER BY id DESC")
    complaints = c.fetchall()
    conn.close()

    return render_template("dashboard.html", total=total, unassigned=unassigned,
                           in_progress=in_progress, completed=completed, complaints=complaints)


@app.route('/update/<int:complaint_id>', methods=['POST'])
def update_complaint(complaint_id):
    status = request.form.get("status")
    remarks = request.form.get("remarks")

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ?, remarks = ? WHERE id = ?",
              (status, remarks, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route('/track', methods=['GET', 'POST'])
def track():
    complaints = []
    if request.method == 'POST':
        mobile = request.form.get("mobile")
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        complaints = c.fetchall()
        conn.close()
    return render_template("track.html", complaints=complaints)


@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    mobile = data.get('mobile')
    message = data.get('message')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, email, mobile, message) VALUES (?, ?, ?, ?)",
              (name, email, mobile, message))
    conn.commit()
    conn.close()

    return jsonify({"message": "Complaint received"}), 201


# Optional route to manually reset DB (⚠️ Don't use in production unless needed)
@app.route('/init-db')
def manual_init():
    init_db()
    return "Database initialized successfully!"


if __name__ == '__main__':
    app.run(debug=True)
