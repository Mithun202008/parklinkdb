# MongoDB Integration Setup Guide

## ✅ What's Been Updated

Your Flask app has been migrated from SQLite to MongoDB with all functionality preserved:

- **User Registration & Login** - Passwords hashed and stored securely
- **Parking Spots Management** - Owner can list and manage parking spots
- **Bookings System** - Drivers can book parking spots
- **Dashboard Analytics** - Driver and owner dashboards with statistics
- **Sessions** - Secure token-based authentication

## 🔧 Setup Instructions

### Step 1: Update MongoDB Connection String

Open `app.py` and find line ~36:

```python
MONGO_URI = "mongodb+srv://mithun:<db_password>@cluster0.2o6goxy.mongodb.net/?appName=Cluster0"
```

**Replace `<db_password>` with your MongoDB Atlas password**, like:

```python
MONGO_URI = "mongodb+srv://mithun:YourActualPassword123@cluster0.2o6goxy.mongodb.net/?appName=Cluster0"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
python app.py
```

You should see:
```
✅ Connected to MongoDB successfully!
✅ MongoDB collections and indexes created!
✅ Demo data seeded!
✅ ParkLink backend ready with MongoDB!
🌐 Open http://localhost:5000 in your browser
```

## 📊 Collections in MongoDB

Your database has 4 main collections:

### `users` - Stores user data
```javascript
{
  "_id": ObjectId,
  "name": "John Doe",
  "email": "john@example.com",
  "password": "hashed_password",
  "role": "driver" | "owner",
  "vehicle_no": "TN01AB1234",
  "property_type": "Commercial",
  "notifications": 1,
  "created_at": ISODate()
}
```

### `spots` - Parking spot listings
```javascript
{
  "_id": ObjectId,
  "owner_id": ObjectId,
  "name": "Central Garage",
  "address": "Anna Salai, Chennai",
  "total_spots": 40,
  "available": 36,
  "peak_rate": 50,
  "offpeak_rate": 35,
  "weekend_rate": 45,
  "emoji": "🏙️",
  "status": "active",
  "created_at": ISODate()
}
```

### `bookings` - Parking reservations
```javascript
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "spot_id": ObjectId,
  "date": "2026-04-10",
  "time_from": "09:00",
  "time_to": "11:00",
  "duration_hrs": 2,
  "amount": 100,
  "payment_method": "UPI",
  "bank": "State Bank of India",
  "status": "confirmed" | "active" | "completed" | "cancelled",
  "created_at": ISODate()
}
```

### `sessions` - Authentication tokens
```javascript
{
  "token": "hex_token_string",
  "user_id": ObjectId,
  "expires_at": ISODate()  // TTL index auto-deletes after 7 days
}
```

## 🔐 Security Best Practices

1. **Never commit** the password in app.py
2. **Use environment variables** in production:
   ```python
   import os
   MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://mithun:password@cluster0.2o6goxy.mongodb.net/?appName=Cluster0")
   ```

3. **Passwords are hashed** using SHA-256 (for production, use bcrypt)
4. **Sessions expire** after 7 days automatically

## 🧪 Testing the API

### Register a new user
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"password123","role":"driver"}'
```

### Login
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Get user info (use token from login)
```bash
curl -X GET http://localhost:5000/api/me \
  -H "X-Auth-Token: YOUR_TOKEN_HERE"
```

### View parking spots
```bash
curl http://localhost:5000/api/spots
```

## ✨ Demo Data

When you first run the app, it seeds demo data:
- **Owner Account**: `owner@parklink.in` / `demo1234`
- **4 Sample Parking Spots** with different rates and locations

## 📝 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register` | ❌ | Register new user |
| POST | `/api/login` | ❌ | Login user |
| POST | `/api/logout` | ✅ | Logout user |
| GET | `/api/me` | ✅ | Get current user info |
| GET | `/api/spots` | ❌ | List all active spots |
| POST | `/api/spots` | ✅ | Create new spot (owners) |
| GET | `/api/my-spots` | ✅ | Get owner's spots |
| POST | `/api/bookings` | ✅ | Create booking |
| GET | `/api/my-bookings` | ✅ | Get user's bookings |
| PUT | `/api/bookings/<id>/cancel` | ✅ | Cancel booking |
| GET | `/api/dashboard` | ✅ | Get dashboard stats |

## 🛠️ Troubleshooting

**Error: "Connection refused"**
- Check MongoDB Atlas is running
- Verify internet connection
- Check password is correct

**Error: "Unauthorized"**
- Token may have expired (7 days)
- Try logging in again

**Error: "Email already registered"**
- Email already exists in database
- Try with different email

## 📚 Next Steps

1. ✅ Update MongoDB password in app.py
2. ✅ Run `pip install -r requirements.txt`
3. ✅ Execute `python app.py`
4. ✅ Test the API with provided examples
5. ✅ Build your frontend to use these endpoints

Good luck! 🚀
