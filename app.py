from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
db_initialized = False  # Track if DB is initialized

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            complaint TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def before_any_request():
    global db_initialized
    if not db_initialized:
        init_db()
        db_initialized = True

@app.route('/')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM complaints')
    total_complaints = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'")
    pending_complaints = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved_complaints = c.fetchone()[0]

    conn.close()

    return render_template(
        'dashboard.html',
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        resolved_complaints=resolved_complaints
    )

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']
    complaint = request.form['complaint']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, address, complaint) VALUES (?, ?, ?, ?)",
              (name, mobile, address, complaint))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        mobile = request.form['mobile']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        results = c.fetchall()
        conn.close()
        return render_template('track.html', results=results)
    return render_template('track.html', results=None)

@app.route('/update/<int:complaint_id>', methods=['POST'])
def update(complaint_id):
    status = request.form['status']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=False)
