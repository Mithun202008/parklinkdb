"""
ParkLink - Flask Backend with MongoDB
Run: python app.py
Visit: http://localhost:5000
"""

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

@app.after_request
def cors_after(response):
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Auth-Token'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# ─────────────────────────────────────────────
# MONGODB SETUP
# ─────────────────────────────────────────────

# MongoDB Atlas connection with URL-encoded password
MONGO_URI = "mongodb+srv://mithun:mithun%4019577@cluster0.2o6goxy.mongodb.net/?appName=Cluster0"
DB_NAME = "parklink"

try:
    client = MongoClient(os.environ.get("MONGO_URI"))
    db = client[DB_NAME]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
    print("Make sure to update MONGO_URI with your actual MongoDB password in app.py")

def init_db():
    """Initialize MongoDB collections and indexes"""
    try:
        # Create collections if they don't exist
        if "users" not in db.list_collection_names():
            db.create_collection("users")
        if "spots" not in db.list_collection_names():
            db.create_collection("spots")
        if "bookings" not in db.list_collection_names():
            db.create_collection("bookings")
        if "sessions" not in db.list_collection_names():
            db.create_collection("sessions")

        # Create indexes for better query performance
        db.users.create_index("email", unique=True)
        db.sessions.create_index("expires_at", expireAfterSeconds=0)  # TTL index
        db.bookings.create_index([("user_id", 1), ("spot_id", 1)])

        print("✅ MongoDB collections and indexes created!")

        # Seed demo data if empty
        if db.users.count_documents({}) == 0:
            pw = hashlib.sha256("demo1234".encode()).hexdigest()
            owner = db.users.insert_one({
                "name": "Demo Owner",
                "email": "owner@parklink.in",
                "password": pw,
                "role": "owner",
                "property_type": "Commercial Building",
                "vehicle_no": None,
                "notifications": 1,
                "created_at": datetime.now()
            })

            owner_id = owner.inserted_id
            seed_spots = [
                {
                    "owner_id": owner_id,
                    "name": "Central Garage",
                    "address": "Anna Salai, Chennai",
                    "total_spots": 40,
                    "available": 36,
                    "peak_rate": 50,
                    "offpeak_rate": 35,
                    "weekend_rate": 45,
                    "emoji": "🏙️",
                    "status": "active",
                    "created_at": datetime.now()
                },
                {
                    "owner_id": owner_id,
                    "name": "Phoenix Mall Parking",
                    "address": "Velachery, Chennai",
                    "total_spots": 80,
                    "available": 72,
                    "peak_rate": 70,
                    "offpeak_rate": 50,
                    "weekend_rate": 60,
                    "emoji": "🛍️",
                    "status": "active",
                    "created_at": datetime.now()
                },
                {
                    "owner_id": owner_id,
                    "name": "T-Nagar Basement",
                    "address": "T-Nagar, Chennai",
                    "total_spots": 30,
                    "available": 18,
                    "peak_rate": 40,
                    "offpeak_rate": 28,
                    "weekend_rate": 35,
                    "emoji": "🏢",
                    "status": "active",
                    "created_at": datetime.now()
                },
                {
                    "owner_id": owner_id,
                    "name": "Adyar Open Lot",
                    "address": "Adyar, Chennai",
                    "total_spots": 20,
                    "available": 14,
                    "peak_rate": 60,
                    "offpeak_rate": 40,
                    "weekend_rate": 50,
                    "emoji": "🌳",
                    "status": "active",
                    "created_at": datetime.now()
                }
            ]
            db.spots.insert_many(seed_spots)
            print("✅ Demo data seeded!")
    except Exception as e:
        print(f"Error initializing DB: {e}")

# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────

def convert_objectid(obj):
    """Convert ObjectId and datetime to JSON-serializable formats"""
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def create_session(user_id):
    token = secrets.token_hex(32)
    expires = datetime.now() + timedelta(days=7)
    db.sessions.insert_one({
        "token": token,
        "user_id": user_id,
        "expires_at": expires
    })
    return token

def get_user_from_token(token):
    if not token:
        return None
    session_doc = db.sessions.find_one({
        "token": token,
        "expires_at": {"$gt": datetime.now()}
    })
    if not session_doc:
        return None
    user = db.users.find_one({"_id": session_doc["user_id"]})
    if user:
        user["id"] = str(user["_id"])  # For compatibility
    return user

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Auth-Token") or request.cookies.get("parklink_token")
        user = get_user_from_token(token)
        if not user:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# ROUTES — SERVE FRONTEND
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─────────────────────────────────────────────
# AUTH API
# ─────────────────────────────────────────────

@app.route("/api/register", methods=["POST", "OPTIONS"])
def register():
    data = request.get_json()
    name   = (data.get("name") or "").strip()
    email  = (data.get("email") or "").strip().lower()
    pw     = (data.get("password") or "").strip()
    role   = data.get("role", "driver")
    vehicle = data.get("vehicle_no", "")
    prop_type = data.get("property_type", "")
    notif  = int(data.get("notifications", 1))

    if not name or not email or not pw:
        return jsonify({"error": "Name, email, and password are required."}), 400
    if len(pw) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if role not in ("driver", "owner"):
        return jsonify({"error": "Invalid role."}), 400

    # Check if email already exists
    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({"error": "Email already registered."}), 409

    # Insert new user
    result = db.users.insert_one({
        "name": name,
        "email": email,
        "password": hash_pw(pw),
        "role": role,
        "vehicle_no": vehicle if vehicle else None,
        "property_type": prop_type if prop_type else None,
        "notifications": notif,
        "created_at": datetime.now()
    })

    user = db.users.find_one({"_id": result.inserted_id})
    token = create_session(result.inserted_id)
    
    resp = jsonify({
        "message": f"Welcome, {name}!",
        "user": {
            "id": str(user["_id"]),
            "name": name,
            "email": email,
            "role": role
        },
        "token": token
    })
    resp.set_cookie("parklink_token", token, httponly=True, samesite="Lax", max_age=60*60*24*7)
    return resp, 201

@app.route("/api/login", methods=["POST", "OPTIONS"])
def login():
    data  = request.get_json()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password") or "").strip()

    if not email or not pw:
        return jsonify({"error": "Email and password required."}), 400

    user = db.users.find_one({
        "email": email,
        "password": hash_pw(pw)
    })
    
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    token = create_session(user["_id"])
    resp = jsonify({
        "message": f"Welcome back, {user['name']}!",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": email,
            "role": user["role"]
        },
        "token": token
    })
    resp.set_cookie("parklink_token", token, httponly=True, samesite="Lax", max_age=60*60*24*7)
    return resp

@app.route("/api/logout", methods=["POST"])
def logout():
    token = request.headers.get("X-Auth-Token") or request.cookies.get("parklink_token")
    if token:
        db.sessions.delete_one({"token": token})
    resp = jsonify({"message": "Logged out."})
    resp.delete_cookie("parklink_token")
    return resp

@app.route("/api/me", methods=["GET"])
@auth_required
def me():
    u = request.current_user
    return jsonify({
        "id": u["id"],
        "name": u["name"],
        "email": u["email"],
        "role": u["role"],
        "vehicle_no": u.get("vehicle_no"),
        "property_type": u.get("property_type")
    })

# ─────────────────────────────────────────────
# SPOTS API
# ─────────────────────────────────────────────

@app.route("/api/spots", methods=["GET"])
def get_spots():
    spots = list(db.spots.aggregate([
        {"$match": {"status": "active"}},
        {"$lookup": {
            "from": "users",
            "localField": "owner_id",
            "foreignField": "_id",
            "as": "owner"
        }},
        {"$unwind": "$owner"},
        {"$project": {
            "id": "$_id",
            "name": 1,
            "address": 1,
            "total_spots": 1,
            "available": 1,
            "peak_rate": 1,
            "offpeak_rate": 1,
            "weekend_rate": 1,
            "emoji": 1,
            "status": 1,
            "owner_name": "$owner.name",
            "created_at": 1
        }}
    ]))
    
    return jsonify(convert_objectid(spots))

@app.route("/api/spots/<spot_id>", methods=["GET"])
def get_spot(spot_id):
    try:
        spot = db.spots.find_one({"_id": ObjectId(spot_id)})
        if not spot:
            return jsonify({"error": "Spot not found."}), 404
        return jsonify(convert_objectid(spot))
    except:
        return jsonify({"error": "Invalid spot ID."}), 400

@app.route("/api/spots/<spot_id>/availability", methods=["GET"])
def spot_availability(spot_id):
    date = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    try:
        spot = db.spots.find_one({
            "_id": ObjectId(spot_id),
            "status": "active"
        })
        if not spot:
            return jsonify({"error": "Spot not found."}), 404

        bookings = list(db.bookings.find({
            "spot_id": ObjectId(spot_id),
            "date": date,
            "status": {"$ne": "cancelled"}
        }, {"time_from": 1, "time_to": 1}))

        def to_minutes(t):
            try:
                h, m = map(int, t.split(':'))
                return h * 60 + m
            except:
                return 0

        booked_intervals = sorted((to_minutes(b['time_from']), to_minutes(b['time_to'])) for b in bookings)
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if date == today:
            current_min = now.hour * 60 + now.minute
        else:
            current_min = 6 * 60

        business_start = 6 * 60
        business_end = 22 * 60
        cursor = max(business_start, current_min)
        free_ranges = []

        for start, end in booked_intervals:
            if end <= cursor:
                continue
            if start > cursor:
                free_ranges.append((cursor, min(start, business_end)))
            cursor = max(cursor, end)
            if cursor >= business_end:
                break

        if cursor < business_end:
            free_ranges.append((cursor, business_end))

        available_slots = []
        import random
        rng = random.Random(int(now.timestamp() // 60))

        def build_random_slots(window_start, window_end, max_slots=6):
            slots = []
            start = window_start
            while start + 60 <= window_end and len(slots) < max_slots:
                max_duration = min(180, window_end - start)
                duration = rng.choice([60, 90, 120])
                duration = min(duration, max_duration)
                if duration < 60:
                    break
                end = start + duration
                slots.append({
                    "date": date,
                    "from": f"{start // 60:02d}:{start % 60:02d}",
                    "to": f"{end // 60:02d}:{end % 60:02d}"
                })
                start = end + rng.randint(30, 90)
            return slots

        if not free_ranges:
            free_ranges = [(max(business_start, current_min), business_end)]

        for start, end in free_ranges:
            length = end - start
            if length < 60:
                continue
            available_slots.extend(build_random_slots(start, end))

        if not available_slots and current_min + 60 <= business_end:
            available_slots = build_random_slots(max(business_start, current_min), business_end)

        return jsonify({"date": date, "available_slots": available_slots})
    except Exception as e:
        print(f"❌ Availability Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/api/spots", methods=["POST"])
@auth_required
def add_spot():
    user = request.current_user
    if user["role"] != "owner":
        return jsonify({"error": "Only owners can list spots."}), 403

    data = request.get_json()
    name  = (data.get("name") or "").strip()
    addr  = (data.get("address") or "").strip()
    total = int(data.get("total_spots") or 10)

    if not name or not addr:
        return jsonify({"error": "Name and address are required."}), 400

    result = db.spots.insert_one({
        "owner_id": ObjectId(user["_id"]),
        "name": name,
        "address": addr,
        "total_spots": total,
        "available": total,
        "peak_rate": 9.0,
        "offpeak_rate": 6.0,
        "weekend_rate": 7.0,
        "emoji": "🏢",
        "status": "active",
        "created_at": datetime.now()
    })

    spot = db.spots.find_one({"_id": result.inserted_id})
    return jsonify(convert_objectid(spot)), 201

@app.route("/api/spots/<spot_id>/rates", methods=["PUT"])
@auth_required
def update_rates(spot_id):
    user = request.current_user
    try:
        spot = db.spots.find_one({
            "_id": ObjectId(spot_id),
            "owner_id": ObjectId(user["_id"])
        })
        if not spot:
            return jsonify({"error": "Spot not found or not yours."}), 404

        data = request.get_json()
        db.spots.update_one(
            {"_id": ObjectId(spot_id)},
            {"$set": {
                "peak_rate": data.get("peak_rate", spot["peak_rate"]),
                "offpeak_rate": data.get("offpeak_rate", spot["offpeak_rate"]),
                "weekend_rate": data.get("weekend_rate", spot["weekend_rate"])
            }}
        )
        return jsonify({"message": "Rates updated successfully."})
    except:
        return jsonify({"error": "Invalid spot ID."}), 400

@app.route("/api/my-spots", methods=["GET"])
@auth_required
def my_spots():
    user = request.current_user
    spots = list(db.spots.aggregate([
        {"$match": {"owner_id": ObjectId(user["_id"])}},
        {"$lookup": {
            "from": "bookings",
            "localField": "_id",
            "foreignField": "spot_id",
            "as": "bookings"
        }},
        {"$project": {
            "id": "$_id",
            "name": 1,
            "address": 1,
            "total_spots": 1,
            "available": 1,
            "peak_rate": 1,
            "offpeak_rate": 1,
            "weekend_rate": 1,
            "emoji": 1,
            "status": 1,
            "total_bookings": {"$size": "$bookings"},
            "total_revenue": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$bookings.status", "completed"]},
                        "$bookings.amount",
                        0
                    ]
                }
            },
            "created_at": 1
        }}
    ]))
    
    return jsonify(convert_objectid(spots))

# ─────────────────────────────────────────────
# BOOKINGS API
# ─────────────────────────────────────────────

@app.route("/api/bookings", methods=["POST", "OPTIONS"])
@auth_required
def create_booking():
    user = request.current_user
    data = request.get_json()

    spot_id        = data.get("spot_id")
    date           = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    time_from      = data.get("time_from") or "09:00"
    time_to        = data.get("time_to")   or "10:00"
    payment_method = data.get("payment_method", "UPI")
    bank           = data.get("bank", "State Bank of India")

    if not spot_id:
        return jsonify({"error": "spot_id is required."}), 400

    # Validate bank selection
    valid_banks = ["ICICI Bank", "Canara Bank", "Indian Bank", "State Bank of India"]
    if bank not in valid_banks:
        return jsonify({"error": "Invalid Bank Selection. Please choose from the approved list."}), 400

    # Calculate duration
    fh, fm = map(int, time_from.split(":"))
    th, tm = map(int, time_to.split(":"))
    dur_min = (th * 60 + tm) - (fh * 60 + fm)
    if dur_min <= 0:
        return jsonify({"error": "Invalid time range."}), 400
    dur_hrs = max(1, -(-dur_min // 60))  # ceiling division

    try:
        spot = db.spots.find_one({
            "_id": ObjectId(spot_id),
            "status": "active"
        })
        if not spot:
            return jsonify({"error": "Spot not found or unavailable."}), 404

        if spot["available"] <= 0:
            return jsonify({"error": "No spots available at this location."}), 409

        # Use weekend rate if applicable
        try:
            day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()
        except Exception:
            day_of_week = datetime.now().weekday()

        if day_of_week >= 5:
            rate = spot["weekend_rate"]
        elif fh >= 18 or fh < 8:
            rate = spot["offpeak_rate"]
        else:
            rate = spot["peak_rate"]

        amount = round(dur_hrs * rate, 2)

        result = db.bookings.insert_one({
            "user_id": ObjectId(user["_id"]),
            "spot_id": ObjectId(spot_id),
            "date": date,
            "time_from": time_from,
            "time_to": time_to,
            "duration_hrs": dur_hrs,
            "amount": amount,
            "payment_method": payment_method,
            "bank": bank,
            "status": "confirmed",
            "created_at": datetime.now()
        })

        db.spots.update_one(
            {"_id": ObjectId(spot_id)},
            {"$inc": {"available": -1}}
        )

        # Fetch booking with spot details
        booking = db.bookings.aggregate([
            {"$match": {"_id": result.inserted_id}},
            {"$lookup": {
                "from": "spots",
                "localField": "spot_id",
                "foreignField": "_id",
                "as": "spot"
            }},
            {"$unwind": "$spot"},
            {"$project": {
                "id": "$_id",
                "user_id": 1,
                "spot_id": 1,
                "date": 1,
                "time_from": 1,
                "time_to": 1,
                "duration_hrs": 1,
                "amount": 1,
                "payment_method": 1,
                "bank": 1,
                "status": 1,
                "spot_name": "$spot.name",
                "spot_address": "$spot.address",
                "created_at": 1
            }}
        ])

        booking_dict = next(booking)
        booking_dict = convert_objectid(booking_dict)
        booking_dict['booking_ref'] = f"BK-{booking_dict['id'][-5:].upper()}"
        return jsonify(booking_dict), 201
    except Exception as e:
        return jsonify({"error": "Invalid spot ID."}), 400

@app.route("/api/my-bookings", methods=["GET"])
@auth_required
def my_bookings():
    user = request.current_user
    bookings = list(db.bookings.aggregate([
        {"$match": {"user_id": ObjectId(user["_id"])}},
        {"$lookup": {
            "from": "spots",
            "localField": "spot_id",
            "foreignField": "_id",
            "as": "spot"
        }},
        {"$unwind": "$spot"},
        {"$sort": {"created_at": -1}},
        {"$project": {
            "id": "$_id",
            "user_id": 1,
            "spot_id": 1,
            "date": 1,
            "time_from": 1,
            "time_to": 1,
            "duration_hrs": 1,
            "amount": 1,
            "payment_method": 1,
            "bank": 1,
            "status": 1,
            "spot_name": "$spot.name",
            "spot_address": "$spot.address",
            "emoji": "$spot.emoji",
            "created_at": 1
        }}
    ]))
    
    return jsonify(convert_objectid(bookings))

@app.route("/api/bookings/<booking_id>/cancel", methods=["PUT"])
@auth_required
def cancel_booking(booking_id):
    user = request.current_user
    try:
        bk = db.bookings.find_one({
            "_id": ObjectId(booking_id),
            "user_id": ObjectId(user["_id"])
        })
        if not bk:
            return jsonify({"error": "Booking not found."}), 404
        if bk["status"] not in ("confirmed",):
            return jsonify({"error": "Cannot cancel this booking."}), 400

        db.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": "cancelled"}}
        )
        db.spots.update_one(
            {"_id": bk["spot_id"]},
            {"$inc": {"available": 1}}
        )
        return jsonify({"message": "Booking cancelled."})
    except:
        return jsonify({"error": "Invalid booking ID."}), 400

# ─────────────────────────────────────────────
# DASHBOARD / ANALYTICS API
# ─────────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
@auth_required
def dashboard():
    user = request.current_user
    user_id = ObjectId(user["_id"])

    if user["role"] == "driver":
        # Driver Dashboard
        stats_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_bookings": {"$sum": 1},
                "total_spent": {"$sum": "$amount"},
                "active_now": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}}
            }}
        ]
        stats = next(db.bookings.aggregate(stats_pipeline), {
            "total_bookings": 0,
            "total_spent": 0,
            "active_now": 0
        })

        recent = list(db.bookings.aggregate([
            {"$match": {"user_id": user_id}},
            {"$lookup": {
                "from": "spots",
                "localField": "spot_id",
                "foreignField": "_id",
                "as": "spot"
            }},
            {"$unwind": "$spot"},
            {"$sort": {"created_at": -1}},
            {"$limit": 5},
            {"$project": {
                "id": "$_id",
                "date": 1,
                "time_from": 1,
                "time_to": 1,
                "amount": 1,
                "spot_name": "$spot.name",
                "emoji": "$spot.emoji",
                "created_at": 1
            }}
        ]))

        # Weekly activity
        from datetime import datetime, timedelta
        weekly_data = []
        for i in range(7):
            day_date = (datetime.now() - timedelta(days=i)).date()
            dow = day_date.strftime('%w')
            count = db.bookings.count_documents({
                "user_id": user_id,
                "date": day_date.isoformat()
            })
            weekly_data.append({"dow": dow, "cnt": count})

        return jsonify({
            "role": "driver",
            "stats": {
                "total_bookings": stats.get("total_bookings", 0),
                "total_spent": stats.get("total_spent", 0),
                "active_now": stats.get("active_now", 0)
            },
            "recent_bookings": convert_objectid(recent),
            "weekly_activity": weekly_data
        })

    else:  # owner
        # Owner Dashboard
        owner_spots = list(db.spots.find({"owner_id": user_id}, {"_id": 1}))
        spot_ids = [s["_id"] for s in owner_spots] if owner_spots else []

        if spot_ids:
            stats_pipeline = [
                {"$match": {"spot_id": {"$in": spot_ids}}},
                {"$group": {
                    "_id": None,
                    "total_bookings": {"$sum": 1},
                    "total_revenue": {"$sum": "$amount"},
                    "active_bookings": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}}
                }}
            ]
            stats = next(db.bookings.aggregate(stats_pipeline), {
                "total_bookings": 0,
                "total_revenue": 0,
                "active_bookings": 0
            })
        else:
            stats = {"total_bookings": 0, "total_revenue": 0, "active_bookings": 0}

        # Calculate occupancy
        total_spots_agg = list(db.spots.aggregate([
            {"$match": {"owner_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$total_spots"}}}
        ]))
        total_spots = total_spots_agg[0]["total"] if total_spots_agg else 0

        available_agg = list(db.spots.aggregate([
            {"$match": {"owner_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$available"}}}
        ]))
        available_spots = available_agg[0]["total"] if available_agg else 0

        occupied = total_spots - available_spots
        occupancy_pct = round((occupied / total_spots * 100) if total_spots else 0, 1)

        # Weekly activity
        from datetime import datetime, timedelta
        weekly_data = []
        for i in range(7):
            day_date = (datetime.now() - timedelta(days=i)).date()
            day_bookings = list(db.bookings.aggregate([
                {"$match": {
                    "spot_id": {"$in": spot_ids},
                    "date": day_date.isoformat()
                }},
                {"$group": {
                    "_id": None,
                    "cnt": {"$sum": 1},
                    "revenue": {"$sum": "$amount"}
                }}
            ]))
            dow = day_date.strftime('%w')
            if day_bookings:
                weekly_data.append({
                    "dow": dow,
                    "cnt": day_bookings[0].get("cnt", 0),
                    "revenue": day_bookings[0].get("revenue", 0)
                })
            else:
                weekly_data.append({"dow": dow, "cnt": 0, "revenue": 0})

        # Recent bookings
        recent = list(db.bookings.aggregate([
            {"$match": {"spot_id": {"$in": spot_ids}}},
            {"$lookup": {
                "from": "spots",
                "localField": "spot_id",
                "foreignField": "_id",
                "as": "spot"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$spot"},
            {"$unwind": "$user"},
            {"$sort": {"created_at": -1}},
            {"$limit": 8},
            {"$project": {
                "id": "$_id",
                "date": 1,
                "time_from": 1,
                "time_to": 1,
                "amount": 1,
                "status": 1,
                "spot_name": "$spot.name",
                "driver_name": "$user.name",
                "created_at": 1
            }}
        ]))

        return jsonify({
            "role": "owner",
            "stats": {
                "total_bookings": stats.get("total_bookings", 0),
                "total_revenue": stats.get("total_revenue", 0),
                "active_bookings": stats.get("active_bookings", 0),
                "occupancy_pct": occupancy_pct,
                "total_spots": total_spots,
                "available_spots": available_spots
            },
            "weekly_activity": weekly_data,
            "recent_bookings": convert_objectid(recent)
        })

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n✅  ParkLink backend ready with MongoDB!")
    print("🌐  Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
