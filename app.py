from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "complaints.db"

# ✅ Initialize DB
def init_db():
    if not os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    phone TEXT,
                    issue TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'Unassigned',
                    comment TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

# ✅ Save complaint
def save_complaint(name, phone, issue, location):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (name, phone, issue, location)
            VALUES (?, ?, ?, ?)
        """, (name, phone, issue, location))
        conn.commit()

# ✅ Dashboard Stats + Complaints
def get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Unassigned'")
        unassigned = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
        in_progress = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Completed'")
        completed = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = cursor.fetchall()

    return total, unassigned, in_progress, completed, complaints

# ✅ Routes
@app.route('/')
def dashboard():
    total, unassigned, in_progress, completed, complaints = get_stats()
    return render_template("dashboard.html", total=total, unassigned=unassigned,
                           in_progress=in_progress, completed=completed,
                           complaints=complaints)

@app.route('/track')
def track():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = cursor.fetchall()
    return render_template("track.html", complaints=complaints)

@app.route('/update/<int:complaint_id>', methods=['POST'])
def update_complaint(complaint_id):
    status = request.form.get("status")
    comment = request.form.get("comment")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE complaints
            SET status = ?, comment = ?
            WHERE id = ?
        """, (status, comment, complaint_id))
        conn.commit()
    return redirect(url_for('track'))

# ✅ WhatsApp Flow endpoint
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "Unknown")
        phone = data.get("phone", "Unknown")
        issue = data.get("issue", "Not specified")
        location = data.get("location", "Not specified")
        save_complaint(name, phone, issue, location)
        return jsonify({"status": "received"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
