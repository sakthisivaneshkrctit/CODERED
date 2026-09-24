from flask import Flask, request, jsonify, session, send_from_directory
from datetime import datetime
import uuid
import os

# Initialize Flask
# static_folder='.' means "serve files from the current folder"
app = Flask(__name__, static_folder='.')
app.secret_key = "codered_secret_key_secure_123"

# ==========================================
# 1. DATABASE (Simulated In-Memory)
# ==========================================

users_db = {} 

teachers_db = {
    't1': {'id': 't1', 'name': 'Mr. Sharma', 'subject': 'Python', 'uploads': 0, 'paid_total': 0, 'pending': 0},
    't2': {'id': 't2', 'name': 'Ms. Priya', 'subject': 'C Prog', 'uploads': 0, 'paid_total': 0, 'pending': 0},
    't3': {'id': 't3', 'name': 'Mr. David', 'subject': 'Web Dev', 'uploads': 0, 'paid_total': 0, 'pending': 0}
}

ledger = {
    'total_revenue': 0,
    'spu_investment': 0,
    'student_payouts': 0,
    'salary_paid': 0
}

courses_db = {
    'py': {'id': 'py', 'title': 'Python Mastery', 'price': 2000, 'desc': 'Master Python from basics.', 'style': 'style-green', 'icon': 'fa-python'},
    'c': {'id': 'c', 'title': 'C Programming', 'price': 2000, 'desc': 'Low-level power.', 'style': 'style-blue', 'icon': 'fa-microchip'}
}

# ==========================================
# 2. FILE SERVING ROUTES (The Fix)
# ==========================================

# 1. Root URL -> Index or Login
@app.route('/')
def root():
    if 'user_id' not in session:
        return send_from_directory('.', 'login.html')
    return send_from_directory('.', 'index.html')

# 2. Magic Route -> Serves ANY file requested (wallet.html, game.html, etc.)
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# ==========================================
# 3. API ENDPOINTS (The Logic)
# ==========================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    type_ = data.get('type')

    # Staff
    if type_ == 'staff':
        if email == 'owner' or email == 'admin@codered.com':
            session['role'] = 'owner'
            return jsonify({'success': True, 'redirect': 'owner.html'})
        if email in teachers_db:
            session['user_id'] = email
            session['role'] = 'teacher'
            return jsonify({'success': True, 'redirect': 'teacher.html'})
        return jsonify({'success': False, 'msg': 'Invalid Access'})

    # Signup
    if type_ == 'signup':
        for u in users_db.values():
            if u['email'] == email: return jsonify({'success': False, 'msg': 'User exists'})
        
        uid = str(uuid.uuid4())
        users_db[uid] = {
            'id': uid, 'name': data.get('name'), 'email': email, 'password': password,
            'wallet': 4500, 'courses': [], 'photo': ''
        }
        return jsonify({'success': True, 'msg': 'Created!'})

    # Login
    if type_ == 'login':
        user = next((u for u in users_db.values() if u['email'] == email), None)
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['role'] = 'student'
            return jsonify({'success': True, 'redirect': 'index.html'})
        return jsonify({'success': False, 'msg': 'Invalid Credentials'})

    return jsonify({'success': False})

@app.route('/api/student/me', methods=['GET'])
def get_me():
    uid = session.get('user_id')
    if uid in users_db: return jsonify(users_db[uid])
    return jsonify({'name': 'Guest', 'wallet': 0, 'courses': []})

@app.route('/api/courses', methods=['GET'])
def get_courses_api(): return jsonify(courses_db)

@app.route('/api/student/buy_course', methods=['POST'])
def buy_course():
    uid = session.get('user_id')
    cid = request.json.get('course_id')
    user = users_db.get(uid)
    course = courses_db.get(cid)
    
    if user and course:
        for c in user['courses']:
            if c['course_id'] == cid: return jsonify({'success': False, 'msg': 'Owned'})

        if user['wallet'] >= course['price']:
            user['wallet'] -= course['price']
            ledger['total_revenue'] += course['price']
            ledger['spu_investment'] += (course['price'] / 2)
            user['courses'].append({'course_id': cid, 'paid': True, 'completed': False, 'start_date': datetime.now().isoformat()})
            return jsonify({'success': True})
    return jsonify({'success': False, 'msg': 'Low Balance'})

@app.route('/api/student/complete_battle', methods=['POST'])
def complete_battle():
    uid = session.get('user_id')
    cid = request.json.get('course_id')
    user = users_db.get(uid)
    if user:
        c = next((x for x in user['courses'] if x['course_id'] == cid), None)
        if c and not c['completed']:
            user['wallet'] += 1000
            ledger['student_payouts'] += 1000
            c['completed'] = True
            return jsonify({'success': True, 'msg': 'Victory! ₹1000 Added.'})
    return jsonify({'success': False, 'msg': 'Already done.'})

@app.route('/api/teacher/upload', methods=['POST'])
def teacher_upload():
    tid = request.json.get('teacher_id')
    if tid in teachers_db:
        teachers_db[tid]['uploads'] += 1
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/owner/stats', methods=['GET'])
def get_owner_stats():
    profit = ledger['total_revenue'] - (ledger['spu_investment'] + ledger['student_payouts'] + ledger['salary_paid'])
    return jsonify({
        'revenue': ledger['total_revenue'],
        'spu': ledger['spu_investment'],
        'payouts': ledger['student_payouts'],
        'salaries': ledger['salary_paid'],
        'profit': profit,
        'teachers': teachers_db,
        'students': users_db
    })

@app.route('/api/owner/pay_salary', methods=['POST'])
def pay_salary():
    tid = request.json.get('teacher_id')
    amt = int(request.json.get('amount'))
    t = teachers_db.get(tid)
    earned = t['uploads'] * 100
    due = earned - t['paid_total']
    
    if t and amt <= due:
        t['paid_total'] += amt
        ledger['salary_paid'] += amt
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/student/profile', methods=['POST'])
def update_profile():
    uid = session.get('user_id')
    if uid in users_db:
        users_db[uid].update(request.json)
        return jsonify({'success': True})
    return jsonify({'success': False})

if __name__ == '__main__':
    print("-------------------------------------------------")
    print("CODERED SERVER RUNNING on http://127.0.0.1:5000")
    print("-------------------------------------------------")
    app.run(debug=True)