from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)

# ✅ Initialize the database
def init_db():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    # Complaints table
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            complaint TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # New connections table
    c.execute('''
        CREATE TABLE IF NOT EXISTS new_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT,
            status TEXT DEFAULT 'Requested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def before_request():
    init_db()

# ✅ Dashboard with Priority Calculation
@app.route('/')
def dashboard():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM complaints')
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved = c.fetchone()[0]
    c.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 50")
    recent_complaints_raw = c.fetchall()

    priority_complaints = []
    for comp in recent_complaints_raw:
        mobile = comp[2]
        c.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE mobile = ? AND date(created_at) >= date('now', '-30 day')
        """, (mobile,))
        count_last_30_days = c.fetchone()[0]
        priority = "High" if count_last_30_days >= 3 else "Medium" if count_last_30_days == 2 else "Low"
        priority_complaints.append(comp + (priority,))

    conn.close()
    return render_template('dashboard.html', total=total, pending=pending, resolved=resolved, recent_complaints=priority_complaints)

# ✅ Submit complaint
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    complaint = request.form['complaint']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, complaint) VALUES (?, ?, ?)", (name, mobile, complaint))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ✅ Complaint tracking
@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        mobile = request.form['mobile']
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        complaints = c.fetchall()
        conn.close()
        return render_template('track.html', complaints=complaints)
    return '''
        <form method="POST" action="/track">
            <input type="text" name="mobile" placeholder="Enter your mobile number" required>
            <button type="submit">Track</button>
        </form>
    '''

# ✅ Update complaint status
@app.route('/update_status/<int:complaint_id>/<status>')
def update_status(complaint_id, status):
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ✅ WhatsApp flow integration
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.get_json()
    name = data.get("name")
    mobile = data.get("mobile")
    complaint = data.get("complaint")
    if not all([name, mobile, complaint]):
        return jsonify({"error": "Missing required fields"}), 400
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, complaint) VALUES (?, ?, ?)", (name, mobile, complaint))
    conn.commit()
    conn.close()
    return jsonify({"status": "received"}), 200

# ✅ API to get all new connections
@app.route('/api/new-connections', methods=['GET'])
def api_new_connections():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT * FROM new_connections ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    result = [
        {"id": row[0], "name": row[1], "mobile": row[2], "address": row[3], "status": row[4], "created_at": row[5]}
        for row in data
    ]
    return jsonify(result)

# ✅ Render new connection dashboard
@app.route('/connections', methods=['GET'])
def show_connections():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT * FROM new_connections ORDER BY id DESC")
    connections = c.fetchall()
    conn.close()
    return render_template('connection.html', connections=connections)

# ✅ Lightweight ping
@app.route('/ping')
def ping():
    return 'pong', 200

if __name__ == '__main__':
    app.run(debug=True)
