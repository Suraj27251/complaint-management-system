from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "complaints.db"

# Initialize database if not exists
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                issue TEXT NOT NULL,
                mobile TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT DEFAULT 'Unassigned',
                assigned TEXT DEFAULT '',
                comment TEXT DEFAULT ''
            )
        """)
init_db()

# Admin dashboard
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        complaint_id = request.form.get("id")
        status = request.form.get("status")
        assigned = request.form.get("assigned")
        comment = request.form.get("comment")

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                UPDATE complaints 
                SET status=?, assigned=?, comment=?
                WHERE id=?
            """, (status, assigned, comment, complaint_id))

        return redirect(url_for('dashboard'))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM complaints ORDER BY date DESC")
        complaints = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM complaints")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Unassigned'")
        unassigned = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
        in_progress = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Completed'")
        completed = cur.fetchone()[0]

    return render_template("dashboard.html", total=total, unassigned=unassigned,
                           in_progress=in_progress, completed=completed,
                           complaints=complaints)

# Track complaint (customer side)
@app.route('/track', methods=['GET', 'POST'])
def track():
    result = []
    searched = False

    if request.method == 'POST':
        mobile = request.form.get("mobile", "").strip()
        if mobile.startswith("+91"):
            mobile = mobile[3:]
        elif mobile.startswith("91") and len(mobile) > 10:
            mobile = mobile[2:]

        if len(mobile) == 10:
            with sqlite3.connect(DB_NAME) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM complaints WHERE mobile=? ORDER BY date DESC", (mobile,))
                result = cur.fetchall()
            searched = True

    return render_template("track.html", complaints=result, searched=searched)

# WhatsApp / API complaint submission endpoint
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    try:
        data = request.get_json(force=True)

        name = str(data.get("name", "")).strip()
        issue = str(data.get("issue", "")).strip()
        mobile = str(data.get("mobile", "")).strip()

        if mobile.startswith("+91"):
            mobile = mobile[3:]
        elif mobile.startswith("91") and len(mobile) > 10:
            mobile = mobile[2:]
        mobile = mobile[-10:]  # Ensure it's the last 10 digits

        if not (name and issue and len(mobile) == 10 and mobile.isdigit()):
            return jsonify({"error": "Missing or invalid fields"}), 400

        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO complaints (name, issue, mobile, date)
                VALUES (?, ?, ?, ?)
            """, (name, issue, mobile, date))

        return jsonify({"message": "Complaint received successfully."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Health check
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "UP"}), 200

# Run server locally (for development)
if __name__ == '__main__':
    app.run(debug=True)
