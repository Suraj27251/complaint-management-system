from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ✅ DB init
def init_db():
    with sqlite3.connect("complaints.db") as conn:
        cur = conn.cursor()
        cur.execute("""
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
        conn.commit()

# ✅ Admin dashboard
@app.route('/')
def dashboard():
    conn = sqlite3.connect("complaints.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints")
    complaints = cur.fetchall()
    total = len(complaints)
    unassigned = sum(1 for c in complaints if c[5] == "Unassigned")
    in_progress = sum(1 for c in complaints if c[5] == "In Progress")
    completed = sum(1 for c in complaints if c[5] == "Completed")

    return render_template(
        'dashboard.html',
        complaints=complaints,
        total=total,
        unassigned=unassigned,
        in_progress=in_progress,
        completed=completed
    )

# ✅ Update status
@app.route('/update', methods=['POST'])
def update():
    comp_id = request.form['id']
    status = request.form['status']
    assigned = request.form['assigned']
    comment = request.form['comment']

    conn = sqlite3.connect("complaints.db")
    cur = conn.cursor()
    cur.execute("""
        UPDATE complaints SET status=?, assigned=?, comment=? WHERE id=?
    """, (status, assigned, comment, comp_id))
    conn.commit()
    return redirect(url_for('dashboard'))

# ✅ Public-facing tracking
@app.route('/track', methods=['GET', 'POST'])
def track():
    result = []
    mobile = ""
    if request.method == 'POST':
        mobile = request.form['mobile'].strip()[-10:]
        conn = sqlite3.connect("complaints.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM complaints WHERE mobile LIKE ?", ('%' + mobile,))
        result = cur.fetchall()
    return render_template("track.html", complaints=result, mobile=mobile)

# ✅ Web form (optional)
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        issue = request.form['issue']
        mobile = request.form['mobile'].strip()[-10:]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect("complaints.db")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO complaints (name, issue, mobile, date, status, assigned, comment)
            VALUES (?, ?, ?, ?, 'Unassigned', '', '')
        """, (name, issue, mobile, now))
        conn.commit()
        message = "Complaint submitted successfully!"
    return render_template("register.html", message=message)

# ✅ API: Register complaint (Postman/JSON)
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name = data.get('name')
    issue = data.get('issue')
    mobile = data.get('mobile', '').strip()[-10:]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect("complaints.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints (name, issue, mobile, date, status, assigned, comment)
        VALUES (?, ?, ?, ?, 'Unassigned', '', '')
    """, (name, issue, mobile, now))
    conn.commit()
    return jsonify({'message': 'Complaint registered successfully!'}), 201

# ✅ API: Track complaint via mobile
@app.route('/api/status/<mobile>', methods=['GET'])
def api_status(mobile):
    mobile = mobile.strip()[-10:]
    conn = sqlite3.connect("complaints.db")
    cur = conn.cursor()
    cur.execute("SELECT id, issue, date, status, comment FROM complaints WHERE mobile LIKE ?", ('%' + mobile,))
    complaints = cur.fetchall()
    result = [
        {
            'id': c[0],
            'issue': c[1],
            'date': c[2],
            'status': c[3],
            'comment': c[4]
        } for c in complaints
    ]
    return jsonify({'complaints': result})

# ✅ Initialize DB
init_db()

if __name__ == "__main__":
    app.run(debug=True)
