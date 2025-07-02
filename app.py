from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize the database
def init_db():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            complaint TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def before_request():
    init_db()

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

    # ✅ Get last 50 complaints
    c.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 50")
    complaints_raw = c.fetchall()

    # ✅ Calculate priority
    recent_complaints = []
    for comp in complaints_raw:
        mobile = comp[2]
        # Count complaints from same mobile in last 30 days
        c.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE mobile = ? AND date >= date('now', '-30 days')
        """, (mobile,))
        count_last_30 = c.fetchone()[0]

        if count_last_30 >= 3:
            priority = 'High'
        elif count_last_30 == 2:
            priority = 'Medium'
        else:
            priority = 'Low'

        # Add priority as 6th value in tuple
        comp_with_priority = comp + (priority,)
        recent_complaints.append(comp_with_priority)

    conn.close()
    return render_template('dashboard.html',
                           total=total,
                           pending=pending,
                           resolved=resolved,
                           recent_complaints=recent_complaints)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    complaint = request.form['complaint']

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, complaint) VALUES (?, ?, ?)",
              (name, mobile, complaint))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/track', methods=['POST'])
def track():
    mobile = request.form['mobile']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
    complaints = c.fetchall()
    conn.close()
    return render_template('track.html', complaints=complaints)

@app.route('/track', methods=['GET'])
def track_form():
    return '''
    <form method="POST" action="/track">
        <input type="text" name="mobile" placeholder="Enter your mobile number" required>
        <button type="submit">Track</button>
    </form>
    '''

@app.route('/update_status/<int:complaint_id>/<status>')
def update_status(complaint_id, status):
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

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
    c.execute("INSERT INTO complaints (name, mobile, complaint) VALUES (?, ?, ?)",
              (name, mobile, complaint))
    conn.commit()
    conn.close()

    return jsonify({"status": "received"}), 200

@app.route('/ping')
def ping():
    return 'pong', 200

if __name__ == '__main__':
    app.run(debug=True)
