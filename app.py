from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ✅ Initialize the database and add 'mobile' column if needed
def init_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        issue TEXT,
        mobile TEXT,
        date TEXT,
        status TEXT,
        assigned_to TEXT,
        comment TEXT
    )
    """)

    # Ensure 'mobile' column exists (for older DBs)
    cursor.execute("PRAGMA table_info(complaints)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'mobile' not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN mobile TEXT")

    conn.commit()
    conn.close()

# Call the initializer on app startup
init_db()


# ✅ Admin Dashboard
@app.route('/')
def dashboard():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Unassigned'")
    unassigned = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM complaints ORDER BY id DESC")
    complaints = cursor.fetchall()

    conn.close()
    return render_template("dashboard.html", total=total, unassigned=unassigned,
                           in_progress=in_progress, completed=completed,
                           complaints=complaints)


# ✅ WhatsApp Flow Endpoint
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.get_json()

    name = data.get("name")
    issue = data.get("issue")
    mobile = data.get("mobile")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (name, issue, mobile, date, status, assigned_to, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, issue, mobile, date, "Unassigned", "", ""))
    conn.commit()
    conn.close()

    return {"status": "received"}, 200


# ✅ Admin: Update Complaint
@app.route('/update/<int:complaint_id>', methods=['POST'])
def update_complaint(complaint_id):
    status = request.form.get('status')
    assigned_to = request.form.get('assigned_to')
    comment = request.form.get('comment')

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE complaints
        SET status = ?, assigned_to = ?, comment = ?
        WHERE id = ?
    """, (status, assigned_to, comment, complaint_id))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


# ✅ Customer: Track Complaint using Mobile
@app.route('/track', methods=['GET', 'POST'])
def track():
    complaints = []
    if request.method == 'POST':
        mobile = request.form.get("mobile")
        conn = sqlite3.connect('complaints.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        complaints = cursor.fetchall()
        conn.close()
    return render_template('track.html', complaints=complaints)


if __name__ == '__main__':
    app.run(debug=True)
