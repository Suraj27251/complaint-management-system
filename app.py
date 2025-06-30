from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "complaints.db"

# ✅ Initialize DB
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                issue TEXT,
                mobile TEXT,
                date TEXT,
                status TEXT,
                assigned TEXT,
                comment TEXT
            )
        """)
init_db()

# ✅ Dashboard for Admin
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

        # Stats
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

# ✅ Complaint Tracking by Customer (only 10-digit mobile)
@app.route('/track', methods=['GET', 'POST'])
def track():
    result = []
    searched = False

    if request.method == 'POST':
        mobile = request.form.get("mobile", "").strip()[-10:]
        if mobile:
            with sqlite3.connect(DB_NAME) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM complaints WHERE mobile=? ORDER BY date DESC", (mobile,))
                result = cur.fetchall()
            searched = True

    return render_template("track.html", complaints=result, searched=searched)

# ✅ WhatsApp Flow Endpoint (POST complaint)
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    try:
        data = request.get_json(force=True)
        name = data.get('name')
        issue = data.get('issue')
        mobile = data.get('mobile', '').strip()[-10:]
        date = datetime.now().strftime('%Y-%m-%d %H:%M')

        if not (name and issue and mobile):
            return jsonify({"error": "Missing required fields"}), 400

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO complaints (name, issue, mobile, date, status, assigned, comment)
                VALUES (?, ?, ?, ?, 'Unassigned', '', '')
            """, (name, issue, mobile, date))

        return jsonify({"message": "Complaint received successfully."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Health check route
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"message": "API is working"}), 200

# ✅ Run app (locally)
if __name__ == '__main__':
    app.run(debug=True)
