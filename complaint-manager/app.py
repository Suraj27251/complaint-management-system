from flask import Flask, render_template, request, jsonify, redirect
import sqlite3
from datetime import datetime
import uuid
import os

app = Flask(__name__)
DATABASE = 'database/complaints.db'

# Ensure DB folder exists
os.makedirs('database', exist_ok=True)

# Function to connect to the DB
def db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ HOME PAGE (Complaint Form) ------------------
@app.route('/')
def index():
    return render_template('index.html')

# ------------------ SUBMIT COMPLAINT ------------------
@app.route('/submit', methods=['POST'])
def submit_complaint():
    name = request.form['name']
    phone = request.form['phone']
    issue = request.form['issue']

    ticket_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO complaints 
                      (complaint_id, name, phone, issue, status, timestamp) 
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (ticket_id, name, phone, issue, "Pending", timestamp))
    conn.commit()
    conn.close()

    return render_template('track.html', complaint={
        "complaint_id": ticket_id,
        "name": name,
        "phone": phone,
        "issue": issue,
        "status": "Pending",
        "timestamp": timestamp
    })

# ------------------ TRACK COMPLAINT ------------------
@app.route('/track', methods=['GET', 'POST'])
def track():
    complaint = None
    if request.method == 'POST':
        ticket_id = request.form['ticket_id']
        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE complaint_id=?", (ticket_id,))
        complaint = cursor.fetchone()
        conn.close()
    return render_template('track.html', complaint=complaint)

# ------------------ ADMIN DASHBOARD ------------------
@app.route('/dashboard')
def dashboard():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY timestamp DESC")
    complaints = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', complaints=complaints)

# ------------------ UPDATE STATUS (Admin) ------------------
@app.route('/update_status', methods=['POST'])
def update_status():
    ticket_id = request.form['ticket_id']
    new_status = request.form['status']
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET status=? WHERE complaint_id=?", (new_status, ticket_id))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

# ------------------ WHATSAPP FLOW WEBHOOK ------------------
@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        data = request.get_json()

        # Example key names - update as per your actual WhatsApp Flow
        name = data['entry'][0]['changes'][0]['value']['form_data']['name']
        phone = data['entry'][0]['changes'][0]['value']['form_data']['phone']
        issue = data['entry'][0]['changes'][0]['value']['form_data']['issue']

        ticket_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO complaints 
                          (complaint_id, name, phone, issue, status, timestamp) 
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (ticket_id, name, phone, issue, "Pending", timestamp))
        conn.commit()
        conn.close()

        return jsonify({"message": "Complaint received", "ticket_id": ticket_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
