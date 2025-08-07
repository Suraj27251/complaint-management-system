from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session,
)
import sqlite3
from datetime import datetime
from collections import defaultdict
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret"


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function

# Initialize DB
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'Web'
        )
    ''')

    try:
        c.execute("ALTER TABLE complaints ADD COLUMN source TEXT DEFAULT 'Web'")
    except sqlite3.OperationalError:
        pass

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

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_type TEXT,
        description TEXT,
        quantity INTEGER,
        date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS issued_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device TEXT,
        recipient TEXT,
        date TEXT,
        note TEXT,
        payment_mode TEXT,
        status TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        date TEXT,
        time TEXT,
        action TEXT,
        note TEXT
    )''')

    c.execute(
        '''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )'''
    )

    conn.commit()
    conn.close()

@app.before_request
def before_request():
    init_db()


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template("signup.html", error="All fields are required")
        conn = sqlite3.connect("complaints.db")
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "signup.html", error="Username already exists"
            )
        conn.close()
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = sqlite3.connect("complaints.db")
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["username"] = username
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/')
@login_required
def dashboard():
    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM complaints')
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'")
    pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved = c.fetchone()[0]

    c.execute('''
    SELECT * FROM (
        SELECT * FROM complaints
        WHERE source != 'WhatsApp' OR source IS NULL
        ORDER BY created_at DESC
    )
    GROUP BY mobile
    ORDER BY created_at DESC
    LIMIT 50
''')
    recent_complaints_raw = c.fetchall()

    priority_complaints = []
    for comp in recent_complaints_raw:
        mobile = comp['mobile']
        c.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE mobile = ? AND date(created_at) >= date('now', '-30 day')
        """, (mobile,))
        count = c.fetchone()[0]
        priority = "High" if count >= 3 else "Medium" if count == 2 else "Low"
        priority_complaints.append(dict(comp) | {'priority': priority})

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
        stock_summary[device] = {'stock': stock, 'issued': issued, 'available': stock - issued}

    conn.close()
    return render_template('dashboard.html', total=total, pending=pending, resolved=resolved,
                           recent_complaints=priority_complaints,
                           pending_connections=pending_connections,
                           pending_connection_count=pending_connection_count,
                           stock_summary=stock_summary)
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    complaint = request.form['complaint']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("INSERT INTO complaints (name, mobile, complaint, source) VALUES (?, ?, ?, ?)", (name, mobile, complaint, 'Web'))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/track', methods=['GET', 'POST'])
def track():
    complaints = []
    status = None

    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        name = request.form.get('name', '').strip()

        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()

        if mobile and name:
            c.execute("""
                SELECT id, name, mobile, complaint, status, created_at 
                FROM complaints 
                WHERE mobile = ? AND name LIKE ? 
                ORDER BY created_at DESC
            """, (mobile, f"%{name}%"))
        elif mobile:
            c.execute("""
                SELECT id, name, mobile, complaint, status, created_at 
                FROM complaints 
                WHERE mobile = ? 
                ORDER BY created_at DESC
            """, (mobile,))
        elif name:
            c.execute("""
                SELECT id, name, mobile, complaint, status, created_at 
                FROM complaints 
                WHERE name LIKE ? 
                ORDER BY created_at DESC
            """, (f"%{name}%",))

        complaints = c.fetchall()

        # Calculate worst status in terms of priority
        status_priority = {"Registered": 0, "Pending": 1, "Assigned": 2, "Complete": 3, "Resolved": 3}
        if complaints:
            worst_status_value = max(status_priority.get(comp[4], 0) for comp in complaints)
            status = [key for key, value in status_priority.items() if value == worst_status_value][0]

        conn.close()

    return render_template('track.html', complaints=complaints, status=status)

@app.route('/update_status/<int:complaint_id>/<status>')
@login_required
def update_status(complaint_id, status):
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge')
        return challenge or '', 200

    if request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True)
            if not data:
                return jsonify({"error": "No JSON data received"}), 400

            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    contacts = value.get('contacts', [])
                    messages = value.get('messages', [])

                    if contacts and messages:
                        name = contacts[0].get('profile', {}).get('name', 'Unknown')
                        mobile = contacts[0].get('wa_id', '')
                        message = messages[0].get('text', {}).get('body', '')
                        timestamp_unix = messages[0].get('timestamp')
                        created_at = datetime.fromtimestamp(int(timestamp_unix)).strftime('%Y-%m-%d %H:%M:%S') if timestamp_unix else datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        if name.strip() and name.strip() != '.' and mobile.strip() and message.strip():
                            conn = sqlite3.connect('complaints.db')
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO complaints (name, mobile, complaint, status, created_at, source)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (name, mobile, message, 'Pending', created_at, 'WhatsApp'))
                            conn.commit()
                            conn.close()
            return jsonify({"status": "Message received"}), 200

        except Exception as e:
            return jsonify({"error": "Webhook processing failed"}), 500

@app.after_request
def set_default_json_header(response):
    if request.path.startswith('/webhook') or request.path.startswith('/flow-endpoint'):
        response.headers['Content-Type'] = 'application/json'
    return response

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

@app.route('/complaints', endpoint='complaints_page')
@login_required
def view_complaints():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, mobile, complaint, status, created_at, source 
        FROM complaints 
        WHERE source != 'WhatsApp'
        ORDER BY created_at DESC LIMIT 100
    """)
    complaints = c.fetchall()
    conn.close()
    return render_template('complaints.html', complaints=complaints)

@app.route('/whatsapp')
@login_required
def whatsapp_complaints():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, mobile, complaint, status, created_at 
        FROM complaints 
        WHERE source = 'WhatsApp' 
        ORDER BY created_at DESC
    """)
    complaints = c.fetchall()
    conn.close()

    grouped = defaultdict(list)
    for row in complaints:
        complaint_id, name, mobile, complaint_text, status, created_at = row
        date_key = created_at.split(" ")[0]
        grouped[(mobile, date_key)].append({
            "id": complaint_id,
            "name": name,
            "complaint": complaint_text,
            "status": status,
            "created_at": created_at
        })

    merged_complaints = []
    for (mobile, date), entries in grouped.items():
        merged_complaints.append({
            "id": entries[0]["id"],
            "ids": [str(e["id"]) for e in entries],  # ✅ Added: All grouped IDs
            "name": entries[0]["name"],
            "mobile": mobile,
            "date": date,
            "status": entries[-1]["status"],
            "combined_entries": [e["complaint"] for e in entries],
            "note": ""
        })

    return render_template("WhatsApp.html", complaints=merged_complaints)

@app.route('/new-connections')
@login_required
def new_connections():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, area, status, created_at FROM connection_requests ORDER BY created_at DESC")
    connections = c.fetchall()
    conn.close()
    return render_template('connection.html', connections=connections)

@app.route('/api/new-connection-request', methods=['POST'])
def api_new_connection_request():
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

@app.route('/update-connection-status/<int:connection_id>', methods=['POST'])
@login_required
def update_connection_status(connection_id):
    new_status = request.form['status']
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("UPDATE connection_requests SET status = ? WHERE id = ?", (new_status, connection_id))
    conn.commit()
    conn.close()
    return redirect(url_for('new_connections'))

@app.route('/stock', methods=['GET', 'POST'])
@login_required
def stock():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()

    if request.method == 'POST':
        # ✅ Handle Stock Add or Update
        if 'item_type' in request.form and 'quantity' in request.form:
            item_type = request.form.get('item_type', '').strip()
            description = request.form.get('description', '').strip()
            quantity = int(request.form.get('quantity') or 0)
            stock_date = request.form.get('stock_date') or datetime.now().strftime('%Y-%m-%d')

            if item_type and quantity > 0:
                c.execute("SELECT id FROM stock WHERE item_type = ? AND description = ?", (item_type, description))
                existing = c.fetchone()

                if existing:
                    c.execute(
                        "UPDATE stock SET quantity = quantity + ?, date = ? WHERE id = ?",
                        (quantity, stock_date, existing[0])
                    )
                else:
                    c.execute(
                        "INSERT INTO stock (item_type, description, quantity, date) VALUES (?, ?, ?, ?)",
                        (item_type, description, quantity, stock_date)
                    )
                conn.commit()

        # ✅ Handle Issued Device Record
        elif 'device' in request.form:
            device = request.form.get('device', '').strip()
            recipient = request.form.get('recipient', '').strip()
            date = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
            note = request.form.get('note', '').strip()
            payment_mode = request.form.get('payment_mode', '').strip()
            status = request.form.get('status', '').strip()

            if device and recipient and payment_mode and status:
                c.execute('''
                    INSERT INTO issued_stock (device, recipient, date, note, payment_mode, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (device, recipient, date, note, payment_mode, status))
                conn.commit()

    # ✅ Fetch for display
    c.execute("SELECT item_type, description, quantity, date FROM stock ORDER BY id DESC")
    stock_items = c.fetchall()

    c.execute("SELECT device, recipient, date, note, payment_mode, status FROM issued_stock ORDER BY id DESC LIMIT 20")
    issued_items = c.fetchall()

    conn.close()
    return render_template('stock.html', stock_items=stock_items, issued_items=issued_items)
    # HR dashboard
@app.route('/hr', endpoint='hr_dashboard')
@login_required
def hr_page():
    conn = sqlite3.connect('complaints.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT first_name, last_name, date, time, action, note FROM staff_attendance ORDER BY date DESC, time DESC")
    records = c.fetchall()

    c.execute('''
        SELECT first_name || ' ' || last_name AS name,
               COUNT(DISTINCT date) AS total_days,
               SUM(CASE WHEN action = 'Log in' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN action = 'Absent' THEN 1 ELSE 0 END) AS absent,
               SUM(CASE WHEN action = 'Log in' THEN 1 ELSE 0 END) AS login,
               SUM(CASE WHEN action = 'Log out' THEN 1 ELSE 0 END) AS logout
        FROM staff_attendance
        GROUP BY first_name, last_name
    ''')
    summary = c.fetchall()

    conn.close()
    return render_template('hr.html', records=records, summary=summary)

@app.route('/update_salary', methods=['POST'])
@login_required
def update_salary():
    return redirect(url_for('hr_dashboard'))

@app.route('/staff-attendance-webhook', methods=['POST'])
def staff_attendance_webhook():
    if request.is_json:
        data = request.get_json()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        date = data.get('date')
        time = data.get('time')
        action = data.get('action')
        note = data.get('note')
    else:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date = request.form.get('date')
        time = request.form.get('time')
        action = request.form.get('action')
        note = request.form.get('note')

    if not all([first_name, last_name, date, time, action]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO staff_attendance (first_name, last_name, date, time, action, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (first_name, last_name, date, time, action, note))
    conn.commit()
    conn.close()

    return jsonify({"status": "attendance saved"}), 200

@app.route('/ping')
def ping():
    return 'pong', 200

@app.route('/update_whatsapp_bulk', methods=['POST'])
@login_required
def update_whatsapp_bulk():
    action = request.form.get('action')
    ids = request.form.getlist('selected_ids[]')

    if not ids:
        return redirect(url_for('dashboard'))  # If no IDs, silently redirect

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()

    if action == 'resolve':
        c.executemany("UPDATE complaints SET status = 'Resolved' WHERE id = ?", [(i,) for i in ids])
    elif action == 'delete':
        c.executemany("DELETE FROM complaints WHERE id = ?", [(i,) for i in ids])

    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))  # ✅ Final redirect to dashboard

@app.route('/delete_complaint/<int:complaint_id>', methods=['DELETE'])
@login_required
def delete_complaint(complaint_id):
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute("DELETE FROM complaints WHERE id=?", (complaint_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
