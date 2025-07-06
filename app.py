from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)

# ✅ Initialize the database
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS connection_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            area TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT,
            description TEXT,
            quantity INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS issued_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT,
            recipient TEXT,
            date TEXT,
            note TEXT,
            payment_mode TEXT,
            status TEXT
        )
    ''')

    # ✅ Attendance table for HR
    c.execute('''
        CREATE TABLE IF NOT EXISTS staff_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            date TEXT,
            time TEXT,
            action TEXT
        )
    ''')

    conn.commit()
    conn.close()

@app.before_request
def before_request():
    init_db()

# ✅ Dashboard
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
        count = c.fetchone()[0]

        if count >= 3:
            priority = "High"
        elif count == 2:
            priority = "Medium"
        else:
            priority = "Low"

        priority_complaints.append(comp + (priority,))

    c.execute("SELECT id, name, mobile, area, status, created_at FROM connection_requests WHERE status = 'Pending' ORDER BY created_at DESC LIMIT 5")
    pending_connections = c.fetchall()

    c.execute("SELECT COUNT(*) FROM connection_requests WHERE status = 'Pending'")
    pending_connection_count = c.fetchone()[0]

    device_types = ['Switch', 'WAN Router', 'ONT Router', 'ONU']
    stock_summary = {}
    for device in device_types:
        c.execute("SELECT SUM(quantity) FROM stock WHERE item_type = ?", (device,))
        stock = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM issued_stock WHERE device = ?", (device,))
        issued = c.fetchone()[0] or 0

        stock_summary[device] = {
            'stock': stock,
            'issued': issued,
            'available': stock - issued
        }

    conn.close()
    return render_template('dashboard.html',
        total=total,
        pending=pending,
        resolved=resolved,
        recent_complaints=priority_complaints,
        pending_connections=pending_connections,
        pending_connection_count=pending_connection_count,
        stock_summary=stock_summary
    )

# ✅ Complaint form
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
    complaints = []
    if request.method == 'POST':
        mobile = request.form['mobile']
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        complaints = c.fetchall()
        conn.close()
    return render_template('track.html', complaints=complaints)

# ✅ Update complaint status
@app.route('/update_status/<int:complaint_id>/<status>')
def update_status(complaint_id, status):
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ✅ Webhook for WhatsApp
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        VERIFY_TOKEN = 'complaint_whatsapp_token'
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Verification failed', 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    contacts = value.get('contacts', [])
                    messages = value.get('messages', [])
                    if contacts and messages:
                        name = contacts[0].get('profile', {}).get('name', 'Unknown')
                        mobile = contacts[0].get('wa_id', '')
                        message = messages[0].get('text', {}).get('body', '')

                        conn = sqlite3.connect('complaints.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO complaints (name, mobile, complaint) VALUES (?, ?, ?)", (name, mobile, message))
                        conn.commit()
                        conn.close()
        except Exception as e:
            print("Webhook error:", e)
        return 'EVENT_RECEIVED', 200

# ✅ WhatsApp Flow Test Endpoint
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

# ✅ View all complaints (UI)
@app.route('/complaints')
def view_complaints():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, complaint, status, created_at FROM complaints ORDER BY created_at DESC LIMIT 100")
    complaints = c.fetchall()
    conn.close()
    return render_template('complaints.html', complaints=complaints)

# ✅ New connections page
@app.route('/new-connections')
def new_connections():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, area, status, created_at FROM connection_requests ORDER BY created_at DESC")
    connections = c.fetchall()
    conn.close()
    return render_template('connection.html', connections=connections)

# ✅ API endpoint to get all new connections
@app.route('/api/new-connections')
def api_new_connections():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, area, status, created_at FROM connection_requests ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return jsonify([
        {"id": row[0], "name": row[1], "mobile": row[2], "area": row[3], "status": row[4], "created_at": row[5]}
        for row in rows
    ])

# ✅ Submit new connection request
@app.route('/api/new-connection-request', methods=['POST'])
def new_connection_request():
    data = request.get_json()
    name = data.get("name")
    mobile = data.get("mobile")
    area = data.get("area")

    if not all([name, mobile]):
        return jsonify({"error": "Missing name or mobile"}), 400

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO connection_requests (name, mobile, area) VALUES (?, ?, ?)", (name, mobile, area))
    conn.commit()
    conn.close()
    return jsonify({"status": "received"}), 200

# ✅ Update connection status
@app.route('/update-connection-status/<int:connection_id>', methods=['POST'])
def update_connection_status(connection_id):
    new_status = request.form['status']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE connection_requests SET status = ? WHERE id = ?", (new_status, connection_id))
    conn.commit()
    conn.close()
    return redirect(url_for('new_connections'))

# ✅ Stock page
@app.route('/stock', methods=['GET', 'POST'])
def stock():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()

    if request.method == 'POST':
        if 'item_type' in request.form and 'quantity' in request.form:
            item_type = request.form['item_type']
            description = request.form['description']
            quantity = int(request.form['quantity'])

            c.execute("SELECT id FROM stock WHERE item_type = ? AND description = ?", (item_type, description))
            existing = c.fetchone()
            if existing:
                c.execute("UPDATE stock SET quantity = quantity + ? WHERE id = ?", (quantity, existing[0]))
            else:
                c.execute("INSERT INTO stock (item_type, description, quantity) VALUES (?, ?, ?)", (item_type, description, quantity))
            conn.commit()

        elif 'device' in request.form and 'recipient' in request.form:
            c.execute('''
                INSERT INTO issued_stock (device, recipient, date, note, payment_mode, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request.form['device'],
                request.form['recipient'],
                request.form['date'],
                request.form['note'],
                request.form['payment_mode'],
                request.form['status']
            ))
            conn.commit()

    c.execute("SELECT item_type, description, quantity FROM stock")
    stock_items = c.fetchall()

    c.execute("SELECT device, recipient, date, note, payment_mode, status FROM issued_stock ORDER BY id DESC LIMIT 20")
    issued_items = c.fetchall()

    conn.close()
    return render_template('stock.html', stock_items=stock_items, issued_items=issued_items)

# ✅ HR page
@app.route('/hr', endpoint='hr_dashboard')
def hr_page():
    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row  # ✅ Make rows accessible by name
    c = conn.cursor()

    # Attendance records
    c.execute("SELECT first_name, last_name, date, time, action FROM staff_attendance ORDER BY date DESC, time DESC")
    records = c.fetchall()

    # Monthly summary
    c.execute('''
        SELECT first_name || ' ' || last_name AS name,
            COUNT(DISTINCT date) AS total_days,
            SUM(CASE WHEN action = 'Log in' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN action = 'Absent' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN action = 'Log in' THEN 1 ELSE 0 END) as login,
            SUM(CASE WHEN action = 'Log out' THEN 1 ELSE 0 END) as logout
        FROM staff_attendance
        GROUP BY first_name, last_name
    ''')
    summary = c.fetchall()

    conn.close()
    return render_template('hr.html', records=records, summary=summary)

# ✅ Ping (for uptime monitoring)
@app.route('/ping')
def ping():
    return 'pong', 200

if __name__ == '__main__':
    app.run(debug=True)
