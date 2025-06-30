from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ✅ Initialize database and table if not exists
def init_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        issue TEXT,
        date TEXT,
        status TEXT,
        assigned_to TEXT,
        comment TEXT
    )
    """)
    conn.commit()
    conn.close()

# 🟢 Call DB initializer at startup
init_db()


# 📊 Home Dashboard (Admin View)
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


# 📩 Webhook Endpoint from WhatsApp or other source
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.get_json()
    name = data.get("name")
    issue = data.get("issue")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO complaints (name, issue, date, status, assigned_to, comment) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, issue, date, "Unassigned", "", ""))
    conn.commit()
    conn.close()
    return {"status": "received"}, 200


# 🛠️ Update complaint status (Admin)
@app.route('/update/<int:complaint_id>', methods=['POST'])
def update_complaint(complaint_id):
    status = request.form['status']
    assigned_to = request.form['assigned_to']
    comment = request.form['comment']

    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET status = ?, assigned_to = ?, comment = ? WHERE id = ?",
                   (status, assigned_to, comment, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


# 👤 Track Complaints (Customer View)
@app.route('/track', methods=['GET', 'POST'])
def track():
    complaint = None
    if request.method == 'POST':
        complaint_id = request.form.get("complaint_id")
        conn = sqlite3.connect('complaints.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
        complaint = cursor.fetchone()
        conn.close()
    return render_template('track.html', complaint=complaint)


if __name__ == '__main__':
    app.run(debug=True)
