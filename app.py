from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Ensure database and complaints table exist
def init_db():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    mobile TEXT,
                    address TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'Pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM complaints')
    total_complaints = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'")
    pending_complaints = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
    inprogress_complaints = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved_complaints = c.fetchone()[0]

    c.execute("SELECT * FROM complaints ORDER BY created_at DESC LIMIT 10")
    recent_complaints = c.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total=total_complaints,
                           pending=pending_complaints,
                           inprogress=inprogress_complaints,
                           resolved=resolved_complaints,
                           recent_complaints=recent_complaints)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']
    description = request.form['description']

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, address, description) VALUES (?, ?, ?, ?)",
              (name, mobile, address, description))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/track', methods=['GET', 'POST'])
def track():
    result = None
    if request.method == 'POST':
        mobile = request.form['mobile']
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        result = c.fetchall()
        conn.close()
    return render_template('track.html', result=result)

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    status = request.form['status']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ✅ Custom 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
