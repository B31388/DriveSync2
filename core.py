from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import DriveSyncApp
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

core = Blueprint('core', __name__)
app = DriveSyncApp()

# Default admin credentials (for simplicity; use hashed passwords in production)
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "password123",
    "name": "Default Admin"  # Default name for the admin
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Session contents: {session}")
        if 'admin_logged_in' not in session or 'admin_name' not in session:
            flash("Please log in to access the admin dashboard", "error")
            return redirect(url_for('core.login'))
        return f(*args, **kwargs)
    return decorated_function

@core.route('/')
def index():
    return render_template('index.html')

@core.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == DEFAULT_ADMIN['username'] and password == DEFAULT_ADMIN['password']:
            session['admin_logged_in'] = True
            session['admin_name'] = DEFAULT_ADMIN['name']
            logger.debug(f"Admin logged in: {session['admin_name']}")
            flash("Login successful", "success")
            return redirect(url_for('core.admin_dashboard'))
        else:
            flash("Invalid username or password", "error")
            logger.debug("Login failed: Invalid credentials")
    return render_template('login.html')

@core.route('/logout')
@login_required
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_name', None)
    logger.debug("Admin logged out")
    flash("Logged out successfully", "success")
    return redirect(url_for('core.index'))

@core.route('/admin_dashboard')
@login_required
def admin_dashboard():
    accounts = app.get_all_accounts()
    vehicles = app.get_all_vehicles()
    requests = app.get_all_requests()
    trips = app.get_all_trips()
    return render_template('admin_dashboard.html', accounts=accounts, vehicles=vehicles, requests=requests, trips=trips)

@core.route('/client_dashboard/<client_name>')
def client_dashboard(client_name):
    client = next((c for c in app._clients if c.name == client_name), None)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('core.index'))
    requests = [r.get_details() for r in app._requests if r._client.name == client_name]
    trips = [t.get_trip_details() for t in app._trips if r._request._client.name == client_name]
    return render_template('client_dashboard.html', client=client.get_details(), requests=requests, trips=trips)

@core.route('/driver_dashboard/<driver_name>')
def driver_dashboard(driver_name):
    driver = next((d for d in app._drivers if d.name == driver_name), None)
    if not driver:
        flash("Driver not found", "error")
        return redirect(url_for('core.index'))
    trips = [t.get_trip_details() for t in app._trips if t._driver.name == driver_name]
    return render_template('driver_dashboard.html', driver=driver.get_details(), trips=trips)

@core.route('/add_account', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        if 'admin_name' not in session:
            flash("Session expired. Please log in again.", "error")
            return redirect(url_for('core.login'))
        account_type = request.form['account_type']
        name = request.form['name']
        contact = request.form['contact']
        email = request.form['email']
        try:
            result = app.add_account(session['admin_name'], account_type, name, contact, email)
            if isinstance(result, str):
                flash(result, 'error')
            else:
                flash(f"{account_type.capitalize()} account created for {name}", 'success')
            return redirect(url_for('core.admin_dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('add_account.html')

@core.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        if 'admin_name' not in session:
            flash("Session expired. Please log in again.", "error")
            return redirect(url_for('core.login'))
        registration_number = request.form['registration_number']
        vehicle_type = request.form['vehicle_type']
        fuel_per_km = float(request.form['fuel_per_km'])
        try:
            result = app.add_vehicle(session['admin_name'], registration_number, vehicle_type, fuel_per_km)
            if isinstance(result, str):
                flash(result, 'error')
            else:
                flash(f"Vehicle {registration_number} added", 'success')
            return redirect(url_for('core.admin_dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('add_vehicle.html')

@core.route('/assign_vehicle', methods=['POST'])
@login_required
def assign_vehicle():
    driver_name = request.form['driver_name']
    registration_number = request.form['registration_number']
    result = app.assign_vehicle(driver_name, registration_number)
    flash(result, 'success' if "assigned" in result.lower() else 'error')
    return redirect(url_for('core.admin_dashboard'))

@core.route('/fuel_price', methods=['GET', 'POST'])
@login_required
def fuel_price():
    if request.method == 'POST':
        if 'admin_name' not in session:
            flash("Session expired. Please log in again.", "error")
            return redirect(url_for('core.login'))
        fuel_price = float(request.form['fuel_price'])
        try:
            result = app.set_fuel_price(session['admin_name'], fuel_price)
            flash(result, 'success')
            return redirect(url_for('core.admin_dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('fuel_price.html')

@core.route('/client_request', methods=['GET', 'POST'])
def client_request():
    districts = app.get_districts()  # Get list of districts for dropdowns
    if request.method == 'POST':
        client_name = request.form['client_name']
        client_contact = request.form['client_contact']
        client_email = request.form['client_email']
        goods_description = request.form['goods_description']
        pickup_district = request.form['pickup_district']
        dropoff_district = request.form['dropoff_district']
        spans_night = 'spans_night' in request.form
        result = app.submit_request(
            client_name, client_contact, client_email, goods_description,
            pickup_district, dropoff_district, spans_night
        )
        if isinstance(result, dict):
            flash(result['confirmation'], 'success')
            return redirect(url_for('core.client_dashboard', client_name=client_name))
        else:
            flash(result, 'error')
            return redirect(url_for('core.index'))
    return render_template('client_request.html', districts=districts)

@core.route('/process_request', methods=['POST'])
@login_required
def process_request():
    if 'admin_name' not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('core.login'))
    request_id = request.form['request_id']
    driver_name = request.form['driver_name']
    spans_night = 'spans_night' in request.form
    try:
        result = app.process_request(session['admin_name'], request_id, driver_name, spans_night)
        if isinstance(result, dict):
            flash(result['confirmation'], 'success')
        else:
            flash(result, 'error')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('core.admin_dashboard'))

@core.route('/start_trip', methods=['POST'])
def start_trip():
    driver_name = request.form['driver_name']
    request_id = request.form['request_id']
    result = app.start_trip(driver_name, request_id)
    flash(result, 'success' if "started" in result.lower() else 'error')
    return redirect(url_for('core.driver_dashboard', driver_name=driver_name))

@core.route('/stop_trip', methods=['POST'])
def stop_trip():
    driver_name = request.form['driver_name']
    request_id = request.form['request_id']
    result = app.stop_trip(driver_name, request_id)
    flash(result, 'success' if "completed" in result.lower() else 'error')
    return redirect(url_for('core.driver_dashboard', driver_name=driver_name))