from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)

# ------------------- Database Connection -------------------
def db_connection():
    conn = sqlite3.connect('database/complaints.db')
    return conn

# ------------------- Home Page -------------------
@app.route('/')
def index():
    return render_template('index.html')

# ------------------- Track Complaint Page -------------------
@app.route('/track', methods=['GET', 'POST'])
def track():
    ticket = None
    if request.method == 'POST':
        ticket_id = request.form['ticket_id']
        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE complaint_id=?", (ticket_id,))
        ticket = cursor.fetchone()
        conn.close()
    return render_template('track.html', ticket=ticket)

# ------------------- Admin Dashboard -------------------
@app.route('/dashboard')
def dashboard():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY timestamp DESC")
    complaints = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', complaints=complaints)

# ------------------- WhatsApp Flow Endpoint -------------------
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    try:
        data = request.get_json()

        # Extract WhatsApp form fields — make sure they match your Flow's keys
        name = data['form_data'].get('name')
        phone = data['form_data'].get('phone')
        issue = data['form_data'].get('issue')

        # Generate ticket
        ticket_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save to database
        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (complaint_id, name, phone, issue, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id, name, phone, issue, "Pending", timestamp))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "ticket_id": ticket_id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ------------------- Manual Form Submission (Optional) -------------------
@app.route('/submit', methods=['POST'])
def submit_complaint():
    name = request.form['name']
    phone = request.form['phone']
    issue = request.form['issue']

    ticket_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (complaint_id, name, phone, issue, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ticket_id, name, phone, issue, "Pending", timestamp))
    conn.commit()
    conn.close()

    return redirect('/track')

# ------------------- Health Check -------------------
@app.route('/ping')
def ping():
    return "Server is running!", 200

# ------------------- Run App -------------------
if __name__ == '__main__':
    app.run(debug=True)
