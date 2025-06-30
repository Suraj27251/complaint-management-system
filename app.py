from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "complaints.db"

# ✅ Ensure database is initialized
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

# ✅ Run init_db() when app starts
init_db()

# ✅ Fetch all dashboard statistics
def get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Unassigned'")
        unassigned = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
        in_progress = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Completed'")
        completed = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = cursor.fetchall()

    return total, unassigned, in_progress, completed, complaints

# ✅ Home dashboard route
@app.route('/')
def dashboard():
    total, unassigned, in_progress, completed, complaints = get_stats()
    return render_template('dashboard.html',
                           total=total,
                           unassigned=unassigned,
                           in_progress=in_progress,
                           completed=completed,
                           complaints=complaints)

# ✅ Complaint tracking page
@app.route('/track')
def track():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        complaints = cursor.fetchall()
    return render_template('track.html', complaints=complaints)

# ✅ Admin update status for any complaint
@app.route('/update_status/<int:complaint_id>', methods=['POST'])
def update_status(complaint_id):
    status = request.form['status']
    comment = request.form['comment']
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE complaints SET status=?, comment=? WHERE id=?",
                       (status, comment, complaint_id))
        conn.commit()
    return redirect(url_for('dashboard'))

# ✅ WhatsApp webhook endpoint (POST)
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.json
    name = data.get('name', 'Unknown')
    phone = data.get('phone', '')
    issue = data.get('issue', '')
    location = data.get('location', '')

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (name, phone, issue, location)
            VALUES (?, ?, ?, ?)
        """, (name, phone, issue, location))
        conn.commit()

    return jsonify({"status": "received"}), 200

# ✅ Only run server locally
if __name__ == '__main__':
    app.run(debug=True)
