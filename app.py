import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'hackathon_secret_key'
DATABASE = 'kaamsetu.db'

# --- DATABASE SETUP ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Create Users Table
        db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, phone TEXT UNIQUE, password TEXT, name TEXT, role TEXT)')
        # Create Bookings Table (Includes Price & Image columns)
        db.execute('CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, user_id INTEGER, service_name TEXT, status TEXT, date TEXT, address TEXT, provider_id INTEGER, price TEXT, image TEXT)')
        db.commit()

# --- DATA (Simulated AI Images) ---
services = [
    {"id": 1, "category": "Cleaning", "title": "Deep Home Cleaning", "rating": 4.8, "price": "₹499", "desc": "Complete home sanitization using industrial grade cleaners.", "image": "https://images.unsplash.com/photo-1581578731117-104f2a863cc5?w=500&q=80"},
    {"id": 2, "category": "Cleaning", "title": "Bathroom Cleaning", "rating": 4.6, "price": "₹299", "desc": "Acid-free cleaning for tiles and sanitary ware.", "image": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=500&q=80"},
    {"id": 3, "category": "AC/Appliance", "title": "AC Master Service", "rating": 4.9, "price": "₹599", "desc": "Jet pump cleaning and gas pressure check.", "image": "https://images.unsplash.com/photo-1621905476059-5f812b7a92b4?w=500&q=80"},
    {"id": 4, "category": "Electrician", "title": "Fan Installation", "rating": 4.5, "price": "₹199", "desc": "Secure installation of ceiling or wall fans.", "image": "https://images.unsplash.com/photo-1621905476059-5f812b7a92b4?w=500&q=80"},
    {"id": 5, "category": "Plumbing", "title": "Tap Repair", "rating": 4.4, "price": "₹149", "desc": "Fix leaking taps and washers instantly.", "image": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=500&q=80"},
    {"id": 6, "category": "Carpenter", "title": "Furniture Assembly", "rating": 4.7, "price": "₹349", "desc": "Expert assembly for beds, tables, and chairs.", "image": "https://images.unsplash.com/photo-1621905476059-5f812b7a92b4?w=500&q=80"}
]

categories = [
    {"name": "Cleaning", "icon": "fa-broom"}, 
    {"name": "AC/Appliance", "icon": "fa-snowflake"},
    {"name": "Electrician", "icon": "fa-bolt"}, 
    {"name": "Plumbing", "icon": "fa-faucet"},
    {"name": "Carpenter", "icon": "fa-hammer"}
]

# --- ROUTES ---
@app.route('/')
def root():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') == 'provider': return redirect(url_for('provider_dashboard'))
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE phone = ? AND password = ?', (phone, password)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            if user['role'] == 'provider': return redirect(url_for('provider_dashboard'))
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid Password")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute('INSERT INTO users (phone, password, name, role) VALUES (?, ?, ?, ?)', 
                       (request.form['phone'], request.form['password'], request.form['name'], request.form['role']))
            db.commit()
            return redirect(url_for('login'))
        except: return render_template('signup.html', error="Phone exists!")
    return render_template('signup.html')

# --- USER ROUTES ---
@app.route('/home')
def home():
    if session.get('role') != 'user': return redirect(url_for('root'))
    return render_template('home.html', categories=categories, services=services[:3], active='home', user_name=session['name'])

@app.route('/category/<name>')
def category_page(name):
    filtered = [s for s in services if s['category'] == name]
    return render_template('category_detail.html', services=filtered, category=name)

@app.route('/service/<int:service_id>')
def service_detail(service_id):
    service = next((s for s in services if s['id'] == service_id), None)
    return render_template('service_detail.html', service=service)

@app.route('/book/confirm/<int:service_id>', methods=['GET'])
def confirm_booking(service_id):
    service = next((s for s in services if s['id'] == service_id), None)
    return render_template('booking_confirm.html', service=service)

@app.route('/book/finalize/<int:service_id>', methods=['POST'])
def finalize_booking(service_id):
    service = next((s for s in services if s['id'] == service_id), None)
    db = get_db()
    address = request.form.get('address')
    db.execute('INSERT INTO bookings (user_id, service_name, status, date, address, price, image) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (session['user_id'], service['title'], 'Pending', datetime.now().strftime("%b %d"), address, service['price'], service['image']))
    db.commit()
    return redirect(url_for('bookings'))

@app.route('/bookings')
def bookings():
    db = get_db()
    my_bookings = db.execute('SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    return render_template('bookings.html', bookings=my_bookings, active='bookings')

# --- PROVIDER ROUTES ---
@app.route('/provider')
def provider_dashboard():
    if session.get('role') != 'provider': return redirect(url_for('root'))
    db = get_db()
    pending = db.execute('SELECT * FROM bookings WHERE status = "Pending"').fetchall()
    my_jobs = db.execute('SELECT * FROM bookings WHERE provider_id = ?', (session['user_id'],)).fetchall()
    return render_template('provider_dashboard.html', pending=pending, my_jobs=my_jobs, active='home')

@app.route('/accept/<int:booking_id>')
def accept_job(booking_id):
    db = get_db()
    db.execute('UPDATE bookings SET status = "On The Way", provider_id = ? WHERE id = ?', (session['user_id'], booking_id))
    db.commit()
    return redirect(url_for('provider_dashboard'))

# --- UTILS ---
@app.route('/profile')
def profile():
    return render_template('profile.html', active='profile', user=session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000, host='0.0.0.0')