from geopy.distance import geodesic
from uuid import uuid4
from abc import ABC, abstractmethod
from email_validator import validate_email, EmailNotValidError
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Dictionary of major Ugandan districts with approximate coordinates (latitude, longitude)
UGANDA_DISTRICTS = {
    "Kampala": (0.3476, 32.5825),
    "Wakiso": (0.4025, 32.4789),
    "Mukono": (0.3533, 32.7553),
    "Jinja": (0.4244, 33.2041),
    "Mbale": (1.0784, 34.1810),
    "Gulu": (2.7666, 32.3050),
    "Arua": (3.0201, 30.9111),
    "Mbarara": (-0.6072, 30.6545),
    "Fort Portal": (0.6710, 30.2748),
    "Hoima": (1.4350, 31.3524),
    "Lira": (2.2350, 32.9097),
    "Masaka": (-0.3411, 31.7361),
    "Kasese": (0.1833, 30.0833),
    "Soroti": (1.7222, 33.6111),
    "Kabale": (-1.2410, 29.9850),
}

# Abstract Base Class to enforce abstraction
class Account(ABC):
    def __init__(self, name, contact, email):
        self._account_id = str(uuid4())  # Encapsulation: private attribute
        self._name = None
        self._contact = None
        self._email = None
        self.name = name                # Use setter for validation
        self.contact = contact          # Use setter for validation
        self.email = email              # Use setter for validation

    @abstractmethod
    def get_details(self):
        """Return account details; must be implemented by subclasses."""
        pass

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Name must be a non-empty string")
        self._name = value.strip()

    @property
    def contact(self):
        return self._contact

    @contact.setter
    def contact(self, value):
        if not isinstance(value, str) or not re.match(r'^\+?\d{9,12}$', value):
            raise ValueError("Contact must be a valid phone number (e.g., +256123456789)")
        self._contact = value

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        try:
            validate_email(value, check_deliverability=False)  # Disable deliverability checks
            self._email = value
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email address: {str(e)}")

class Vehicle:
    def __init__(self, registration_number, vehicle_type, fuel_per_km):
        self._registration_number = registration_number
        self._vehicle_type = vehicle_type
        if not isinstance(fuel_per_km, (int, float)) or fuel_per_km <= 0:
            raise ValueError("Fuel per km must be a positive number")
        self._fuel_per_km = fuel_per_km
        self._assigned_driver = None

    @property
    def registration_number(self):
        return self._registration_number

    @property
    def vehicle_type(self):
        return self._vehicle_type

    @property
    def fuel_per_km(self):
        return self._fuel_per_km

    @property
    def assigned_driver(self):
        return self._assigned_driver

    def assign_driver(self, driver):
        self._assigned_driver = driver
        return f"Vehicle {self._registration_number} assigned to {driver.name}"

    def get_details(self):
        return {
            "registration_number": self._registration_number,
            "vehicle_type": self._vehicle_type,
            "fuel_per_km": self._fuel_per_km,
            "assigned_driver": self._assigned_driver.name if self._assigned_driver else "None"
        }

class Driver(Account):
    def __init__(self, name, contact, email):
        super().__init__(name, contact, email)
        self._vehicle = None
        self._trips = []
        self._day_allowance = 10000
        self._night_allowance = 15000

    @property
    def vehicle(self):
        return self._vehicle

    @property
    def day_allowance(self):
        return self._day_allowance

    @property
    def night_allowance(self):
        return self._night_allowance

    def assign_vehicle(self, vehicle):
        if vehicle.assigned_driver and vehicle.assigned_driver != self:
            raise ValueError(f"Vehicle {vehicle.registration_number} is already assigned")
        self._vehicle = vehicle
        vehicle.assign_driver(self)
        return f"Vehicle {vehicle.registration_number} assigned to {self.name}"

    def assign_trip(self, trip):
        if not self._vehicle:
            raise ValueError(f"Driver {self.name} has no assigned vehicle")
        self._trips.append(trip)
        return f"Trip assigned to {self.name}"

    def calculate_total_allowance(self):
        total = sum(
            self._day_allowance + (self._night_allowance if trip.spans_night else 0)
            for trip in self._trips
        )
        return total

    def get_details(self):
        return {
            "account_id": self._account_id,
            "name": self.name,
            "contact": self.contact,
            "email": self.email,
            "vehicle": self._vehicle.registration_number if self._vehicle else "None",
            "trip_count": len(self._trips),
            "total_allowance": self.calculate_total_allowance()
        }

class Client(Account):
    def __init__(self, name, contact, email):
        super().__init__(name, contact, email)
        self._client_number = str(uuid4())
        self._trip_cost = 0
        self._trips = []

    @property
    def client_number(self):
        return self._client_number

    def get_details(self):
        return {
            "account_id": self._account_id,
            "client_number": self._client_number,
            "name": self.name,
            "contact": self.contact,
            "email": self.email,
            "total_trip_cost": self._trip_cost,
            "trip_count": len(self._trips)
        }

    def request_trip(self, trip):
        self._trips.append(trip)
        self._trip_cost += trip.calculate_cost()
        return f"Trip requested by {self.name}, cost: {self._trip_cost} UGX"

class Admin(Account):
    def __init__(self, name, contact, email):
        super().__init__(name, contact, email)

    def get_details(self):
        return {
            "account_id": self._account_id,
            "name": self.name,
            "contact": self.contact,
            "email": self.email,
            "role": "Admin"
        }

class ClientRequest:
    def __init__(self, client, goods_description, pickup_district, dropoff_district):
        self._request_id = str(uuid4())
        self._client = client
        self._goods_description = goods_description
        self._pickup_district = pickup_district  # Store district name
        self._dropoff_district = dropoff_district  # Store district name
        self._pickup_location = UGANDA_DISTRICTS.get(pickup_district)  # Map to coordinates
        self._dropoff_location = UGANDA_DISTRICTS.get(dropoff_district)  # Map to coordinates
        if not self._pickup_location or not self._dropoff_location:
            raise ValueError("Invalid district name provided")
        self._status = "Pending"

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value not in ["Pending", "Assigned", "Completed"]:
            raise ValueError("Invalid status")
        self._status = value

    def get_confirmation(self):
        return f"Request {self._request_id} received for {self._client.name}. Goods: {self._goods_description}. Status: {self._status}"

    def get_details(self):
        return {
            "request_id": self._request_id,
            "client": self._client.name,
            "goods_description": self._goods_description,
            "pickup_district": self._pickup_district,
            "dropoff_district": self._dropoff_district,
            "status": self._status
        }

class Trip:
    def __init__(self, request, driver, spans_night=False):
        self._request = request
        self._driver = driver
        self._spans_night = spans_night
        self._start_location = request._pickup_location  # Coordinates from ClientRequest
        self._end_location = request._dropoff_location  # Coordinates from ClientRequest
        self._fuel_price = None
        self._fuel_per_km = driver.vehicle.fuel_per_km if driver.vehicle else 0
        self._distance = self._calculate_distance()
        self._total_cost = None
        self._status = "Assigned"

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value not in ["Assigned", "Started", "Completed"]:
            raise ValueError("Invalid trip status")
        self._status = value

    def start_trip(self):
        if self._status != "Assigned":
            raise ValueError("Trip can only be started from Assigned status")
        self._status = "Started"
        return f"Trip {self._request._request_id} started by {self._driver.name}"

    def stop_trip(self):
        if self._status != "Started":
            raise ValueError("Trip can only be stopped from Started status")
        self._status = "Completed"
        self._request.status = "Completed"
        return f"Trip {self._request._request_id} completed by {self._driver.name}"

    def set_fuel_price(self, fuel_price):
        if not isinstance(fuel_price, (int, float)) or fuel_price <= 0:
            raise ValueError("Fuel price must be a positive number")
        self._fuel_price = fuel_price
        self._total_cost = self.calculate_cost()

    def _calculate_distance(self):
        try:
            logger.debug(f"Calculating distance between {self._start_location} and {self._end_location}")
            distance = geodesic(self._start_location, self._end_location).kilometers
            logger.debug(f"Distance calculated: {distance} km")
            return distance
        except Exception as e:
            logger.error(f"Distance calculation error: {e}")
            return 0

    def calculate_cost(self):
        if not self._fuel_price or not self._fuel_per_km:
            logger.warning(f"Cannot calculate cost: fuel_price={self._fuel_price}, fuel_per_km={self._fuel_per_km}")
            return 0
        cost = self._distance * self._fuel_per_km * self._fuel_price
        logger.debug(f"Cost calculated: distance={self._distance} km, fuel_per_km={self._fuel_per_km}, fuel_price={self._fuel_price}, cost={cost} UGX")
        return cost

    @property
    def distance(self):
        return self._distance

    @property
    def fuel_price(self):
        return self._fuel_price

    @property
    def total_cost(self):
        return self._total_cost

    @property
    def spans_night(self):
        return self._spans_night

    def get_trip_details(self):
        return {
            "request_id": self._request._request_id,
            "driver": self._driver.name,
            "start_district": self._request._pickup_district,
            "end_district": self._request._dropoff_district,
            "distance": self._distance,
            "fuel_price": self._fuel_price,
            "fuel_per_km": self._fuel_per_km,
            "total_cost": self._total_cost,
            "spans_night": self._spans_night,
            "status": self._status
        }

class DriveSyncApp:
    def __init__(self):
        self._drivers = []
        self._clients = []
        self._admins = []
        self._vehicles = []
        self._requests = []
        self._trips = []
        self._fuel_price = 5000
        # Initialize with a default admin to avoid verification issues
        default_admin = Admin("Default Admin", "+256000000000", "default_admin@example.com")
        self._admins.append(default_admin)

    def _verify_admin(self, admin_name):
        # Allow "Default Admin" to bypass check if no admins exist yet
        if admin_name == "Default Admin":
            return True
        admin = next((a for a in self._admins if a.name == admin_name), None)
        if not admin:
            raise ValueError("Admin not found")
        return admin

    def _verify_driver(self, driver_name):
        driver = next((d for d in self._drivers if d.name == driver_name), None)
        if not driver:
            raise ValueError("Driver not found")
        return driver

    def add_account(self, logged_in_admin_name, account_type, name, contact, email):
        self._verify_admin(logged_in_admin_name)
        try:
            if account_type.lower() == "driver":
                account = Driver(name, contact, email)
                self._drivers.append(account)
            elif account_type.lower() == "admin":
                account = Admin(name, contact, email)
                self._admins.append(account)
            else:
                account = Client(name, contact, email)
                self._clients.append(account)
            return account.get_details()
        except ValueError as e:
            return f"Error creating account: {str(e)}"

    def add_vehicle(self, logged_in_admin_name, registration_number, vehicle_type, fuel_per_km):
        self._verify_admin(logged_in_admin_name)
        if not isinstance(fuel_per_km, (int, float)) or fuel_per_km <= 0:
            raise ValueError("Fuel per km must be a positive number")
        vehicle = Vehicle(registration_number, vehicle_type, fuel_per_km)
        self._vehicles.append(vehicle)
        return vehicle.get_details()

    def assign_vehicle(self, driver_name, registration_number):
        driver = next((d for d in self._drivers if d.name == driver_name), None)
        vehicle = next((v for v in self._vehicles if v.registration_number == registration_number), None)
        if not driver or not vehicle:
            return "Driver or Vehicle not found"
        try:
            return driver.assign_vehicle(vehicle)
        except ValueError as e:
            return str(e)

    def set_fuel_price(self, logged_in_admin_name, fuel_price):
        self._verify_admin(logged_in_admin_name)
        if not isinstance(fuel_price, (int, float)) or fuel_price <= 0:
            raise ValueError("Fuel price must be a positive number")
        self._fuel_price = fuel_price
        return f"Fuel price set to {fuel_price} UGX by {logged_in_admin_name}"

    def submit_request(self, client_name, client_contact, client_email, goods_description, pickup_district, dropoff_district, spans_night=False):
        # Check if client already exists by name
        client = next((c for c in self._clients if c.name.lower() == client_name.lower()), None)
        if not client:
            # Create a new client if not found
            try:
                client = Client(client_name, client_contact, client_email)
                self._clients.append(client)
            except ValueError as e:
                return f"Error creating client: {str(e)}"
        
        request = ClientRequest(client, goods_description, pickup_district, dropoff_district)
        self._requests.append(request)
        return {
            "confirmation": request.get_confirmation(),
            "request": request.get_details()
        }

    def process_request(self, logged_in_admin_name, request_id, driver_name, spans_night=False):
        self._verify_admin(logged_in_admin_name)
        request = next((r for r in self._requests if r._request_id == request_id), None)
        if not request:
            return "Request not found"
        if request.status != "Pending":
            return "Request already processed"
        
        driver = self._verify_driver(driver_name)
        if not driver.vehicle:
            return f"Driver {driver_name} has no assigned vehicle"
        
        trip = Trip(request, driver, spans_night)
        trip.set_fuel_price(self._fuel_price)
        self._trips.append(trip)
        client = request._client
        client.request_trip(trip)
        driver.assign_trip(trip)
        request.status = "Assigned"
        return {
            "confirmation": request.get_confirmation(),
            "request": request.get_details(),
            "trip": trip.get_trip_details()
        }

    def start_trip(self, driver_name, request_id):
        driver = self._verify_driver(driver_name)
        trip = next((t for t in self._trips if t._request._request_id == request_id and t._driver == driver), None)
        if not trip:
            return "Trip not found or not assigned to this driver"
        try:
            return trip.start_trip()
        except ValueError as e:
            return str(e)

    def stop_trip(self, driver_name, request_id):
        driver = self._verify_driver(driver_name)
        trip = next((t for t in self._trips if t._request._request_id == request_id and t._driver == driver), None)
        if not trip:
            return "Trip not found or not assigned to this driver"
        try:
            return trip.stop_trip()
        except ValueError as e:
            return str(e)

    def get_all_accounts(self):
        return {
            "drivers": [d.get_details() for d in self._drivers],
            "clients": [c.get_details() for c in self._clients],
            "admins": [a.get_details() for a in self._admins]
        }

    def get_all_vehicles(self):
        return [v.get_details() for v in self._vehicles]

    def get_all_requests(self):
        return [r.get_details() for r in self._requests]

    def get_all_trips(self):
        return [t.get_trip_details() for t in self._trips]

    def get_districts(self):
        """Return the list of available districts."""
        return sorted(UGANDA_DISTRICTS.keys())