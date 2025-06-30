from flask import Flask, request, render_template, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)

# Home dashboard
@app.route('/')
def dashboard():
    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()

    # Get total complaints
    c.execute('SELECT COUNT(*) FROM complaints')
    total = c.fetchone()[0]

    # Get status counts
    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'unassigned'")
    unassigned = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'in progress'")
    in_progress = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'completed'")
    completed = c.fetchone()[0]

    # Get all complaints for table
    c.execute("SELECT * FROM complaints ORDER BY id DESC")
    complaints = c.fetchall()

    conn.close()
    return render_template(
        'dashboard.html',
        total=total,
        unassigned=unassigned,
        in_progress=in_progress,
        completed=completed,
        complaints=complaints
    )


# Update complaint status
@app.route('/update/<int:complaint_id>', methods=['POST'])
def update_complaint(complaint_id):
    new_status = request.form.get('status')
    if new_status:
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute("UPDATE complaints SET status = ? WHERE id = ?", (new_status, complaint_id))
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))


# Track complaint
@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        conn = sqlite3.connect('complaints.db')
        c = conn.cursor()
        c.execute("SELECT * FROM complaints WHERE mobile = ?", (mobile,))
        complaints = c.fetchall()
        conn.close()
        return render_template('track.html', complaints=complaints, mobile=mobile)
    return render_template('track.html', complaints=None)


# WhatsApp flow endpoint
@app.route('/flow-endpoint', methods=['POST'])
def flow_endpoint():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    message = data.get('message')
    location = data.get('location')

    conn = sqlite3.connect('complaints.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO complaints (name, mobile, message, location, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, mobile, message, location, 'unassigned'))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Complaint received'}), 201


# Run the app (comment out if using gunicorn)
# if __name__ == '__main__':
#     app.run(debug=True)
