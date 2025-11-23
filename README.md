# 🏥 Doctor Assistant ChatBot

An AI-powered chatbot that helps users book doctor appointments at Super Clinic. The system uses OpenAI's GPT models to understand user requests and manages doctor availability through a MySQL database.

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

- **AI-Powered Chat**: Uses OpenAI's GPT-4 mini to understand natural language requests
- **Doctor Booking**: Book appointments with available doctors by specialty and time slot
- **Availability Management**: Check doctor availability across multiple dates
- **Fuzzy Matching**: Intelligently matches user-provided specialties (e.g., "Orthopedist" → "Orthopedic / Chiropractic")
- **Alternative Recommendations**: Suggests alternative slots if the requested time is unavailable
- **Chat History**: Maintains user conversation history for context-aware interactions
- **Single-Port Deployment**: Both frontend and backend run on the same port (8007)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Browser (Frontend)                  │
│            Static HTML/JS/CSS from /dist             │
└────────────────────┬────────────────────────────────┘
                     │ HTTP Requests
                     │
┌────────────────────▼────────────────────────────────┐
│         FastAPI Backend Server (Port 8007)          │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  API Routes (/v1/chat)                       │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  Static Files Serving (/dist folder)        │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
                     │ Database Queries
                     │
        ┌────────────▼──────────────┐
        │  MySQL Database           │
        │  (super_clinic)           │
        │                           │
        │  Tables:                  │
        │  - Speciality             │
        │  - Doctor                 │
        │  - DoctorAvailability     │
        │  - TimeSlots              │
        │  - Patient (Bookings)     │
        └───────────────────────────┘
```

---

## 📦 Prerequisites

### Required Software

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **MySQL 8.0+** - [Download](https://dev.mysql.com/downloads/mysql/)
- **Node.js 14+** (optional, for frontend development) - [Download](https://nodejs.org/)

### Required Accounts

- **OpenAI API Key** - [Get it here](https://platform.openai.com/account/api-keys)

### System Requirements

- RAM: Minimum 2GB (4GB+ recommended)
- Disk Space: 500MB+ for dependencies and database
- Internet Connection: Required for OpenAI API calls

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```powershell
# Open PowerShell or Command Prompt
cd E:\Projects
git clone <repository-url>
cd DoctorAssistantChatBot
```

### Step 2: Create and Activate Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate virtual environment (Windows Command Prompt)
# venv\Scripts\activate.bat
```

### Step 3: Install Python Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

**Key Dependencies:**
- `fastapi>=0.115.0` - Web framework
- `uvicorn[standard]>=0.29.0` - ASGI server
- `sqlalchemy~=2.0.44` - ORM
- `asyncmy>=0.2.9` - Async MySQL driver
- `openai>=1.0.0` - OpenAI API client
- `pydantic~=2.12.4` - Data validation
- `python-dotenv~=1.2.1` - Environment variables

---

## 🗄️ Database Setup

### Step 1: Start MySQL Server

```powershell
# On Windows, MySQL is often in Services
# Or start from MySQL bin directory:
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe"

# Or use MySQL via Docker:
docker run --name mysql_clinic -e MYSQL_ROOT_PASSWORD=test123 -p 3306:3306 -d mysql:latest
```

### Step 2: Create Database and Tables

```powershell
# Open MySQL client
mysql -u root -p

# Enter password: Nilesh@143
```

**Then execute in MySQL:**

```sql
-- Create database
CREATE DATABASE super_clinic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE super_clinic;

-- Create Speciality table
CREATE TABLE Speciality (
    speciality_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(100)
);

-- Create Doctor table
CREATE TABLE Doctor (
    doctor_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(200),
    speciality_id INT NOT NULL,
    FOREIGN KEY (speciality_id) REFERENCES Speciality(speciality_id)
);

-- Create DoctorAvailability table
CREATE TABLE Doctor_Availability (
    availability_id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    available_date DATE NOT NULL,
    FOREIGN KEY (doctor_id) REFERENCES Doctor(doctor_id)
);

-- Create TimeSlots table
CREATE TABLE Time_Slots (
    slot_id INT PRIMARY KEY AUTO_INCREMENT,
    availability_id INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_booked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (availability_id) REFERENCES Doctor_Availability(availability_id)
);

-- Create Patient table (bookings)
CREATE TABLE Patient (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(50) NOT NULL,
    slot_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    FOREIGN KEY (slot_id) REFERENCES Time_Slots(slot_id)
);

-- Sample data: Insert specialties
INSERT INTO Speciality (name, description) VALUES
('Cardiologist', 'Heart specialist'),
('Neurologist', 'Nervous system specialist'),
('Orthopedic / Chiropractic', 'Bone and joint specialist'),
('Dermatologist', 'Skin specialist'),
('Pediatrician', 'Children specialist');

-- Sample data: Insert doctors
INSERT INTO Doctor (name, email, address, speciality_id) VALUES
('Dr. John Smith', 'john@clinic.com', '123 Main St', 1),
('Dr. Sarah Johnson', 'sarah@clinic.com', '456 Oak Ave', 2),
('Dr. Michael Brown', 'michael@clinic.com', '789 Pine Rd', 3),
('Dr. Emily Davis', 'emily@clinic.com', '321 Elm St', 4),
('Dr. Robert Wilson', 'robert@clinic.com', '654 Maple Dr', 5);

-- Sample data: Add doctor availability (next 7 days)
INSERT INTO Doctor_Availability (doctor_id, available_date) VALUES
(1, DATE_ADD(CURDATE(), INTERVAL 1 DAY)),
(1, DATE_ADD(CURDATE(), INTERVAL 2 DAY)),
(1, DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
(2, DATE_ADD(CURDATE(), INTERVAL 1 DAY)),
(2, DATE_ADD(CURDATE(), INTERVAL 4 DAY)),
(3, DATE_ADD(CURDATE(), INTERVAL 2 DAY)),
(3, DATE_ADD(CURDATE(), INTERVAL 5 DAY));

-- Sample data: Add time slots for availability
INSERT INTO Time_Slots (availability_id, start_time, end_time, is_booked) VALUES
(1, '09:00:00', '09:30:00', FALSE),
(1, '10:00:00', '10:30:00', FALSE),
(1, '14:00:00', '14:30:00', FALSE),
(2, '09:00:00', '09:30:00', FALSE),
(2, '11:00:00', '11:30:00', FALSE),
(3, '15:00:00', '15:30:00', FALSE),
(4, '10:00:00', '10:30:00', FALSE),
(5, '13:00:00', '13:30:00', FALSE);

-- Verify tables
SHOW TABLES;
SELECT COUNT(*) as doctor_count FROM Doctor;
SELECT COUNT(*) as slots_count FROM Time_Slots;
```

### Step 3: Verify Database Connection

```powershell
# Test MySQL connection
mysql -u root -pNilesh@143 -h localhost -D super_clinic -e "SHOW TABLES;"
```

---

## ⚙️ Configuration

### Step 1: Create `.env` File

Create a `.env` file in the project root with your configuration:

```env
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_API_KEY_HERE

# Database Configuration (already in Database.py)
# DATABASE_URL=mysql+asyncmy://root:test123@localhost:3306/super_clinic?charset=utf8mb4

# Server Configuration
PORT=8007
HOST=0.0.0.0
```

### Step 2: Update OpenAI API Key

**Option A: Via Environment Variable (Recommended)**
- Add `OPENAI_API_KEY` to your `.env` file (see above)

**Option B: Direct in Code (Not Recommended for Production)**
- Edit `CompletionApiServiceWithDB.py` line 19:
```python
OPENAI_API_KEY = "sk-proj-YOUR_ACTUAL_KEY_HERE"
```

### Step 3: Verify Database Connection

Edit `Database.py` if your MySQL credentials differ:

```python
DATABASE_URL = (
    "mysql+asyncmy://username:password@localhost:3306/super_clinic?charset=utf8mb4"
)
```

---

## ▶️ Running the Application

### Quick Start (All-in-One)

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run the server (serves both frontend and backend on port 8007)
python api_server.py

# Or use Uvicorn directly with reload
uvicorn api_server:app --host 0.0.0.0 --port 8007 --reload
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8007
INFO:     Application startup complete
```

### Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:8007/

---

## 🔌 API Endpoints

### Chat Endpoint

**POST** `/v1/chat`

**Request:**
```json
{
  "userid": "user123",
  "userMessage": "I want to book an appointment with a cardiologist"
}
```

**Response:**
```
Assistant's text response about available doctors and next steps
```

**Example using cURL:**
```powershell
# PowerShell
$body = @{
    userid = "user123"
    userMessage = "Show me available cardiologists"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8007/v1/chat" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Example using Python:**
```python
import requests
import json

url = "http://localhost:8007/v1/chat"
payload = {
    "userid": "user123",
    "userMessage": "Book an appointment with Dr. Smith"
}

response = requests.post(url, json=payload)
print(response.text)
```

---

## 📁 Project Structure

```
DoctorAssistantChatBot/
├── api_server.py                          # Main FastAPI app (serves frontend + backend)
├── CompletionApiServiceWithDB.py          # OpenAI integration & function calling
├── DoctorDetailService.py                 # Business logic for doctors & appointments
├── Database.py                            # MySQL connection & engine setup
├── EntityClasses.py                       # SQLAlchemy ORM models
├── InMemoryChatStoreNew.py               # Chat history storage in memory
├── requirements.txt                       # Python dependencies
├── .env                                   # Environment variables (create this)
├── dist/                                  # Built frontend files
│   ├── index.html
│   ├── assets/
│   ├── favicon.ico
│   └── robots.txt
├── model/
│   └── Doctor_Schema.py                   # Pydantic schemas (if used)
├── venv/                                  # Virtual environment (auto-created)
└── __pycache__/                           # Python cache (auto-generated)
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `api_server.py` | Entry point; FastAPI app serving frontend & APIs |
| `CompletionApiServiceWithDB.py` | OpenAI GPT integration; function calling logic |
| `DoctorDetailService.py` | Database queries; doctor/availability management |
| `Database.py` | MySQL async connection setup |
| `EntityClasses.py` | SQLAlchemy ORM model definitions |
| `InMemoryChatStoreNew.py` | Chat history storage & system prompt |
| `dist/` | Pre-built frontend (HTML/JS/CSS) |

---

## 🔧 Troubleshooting

### Issue 1: 405 Method Not Allowed on /v1/chat

**Cause:** Static files route is intercepting POST requests

**Solution:**
```powershell
# Restart the server - ensure api_server.py has API routes BEFORE static mount
python api_server.py
```

### Issue 2: MySQL Connection Error

```
sqlalchemy.exc.ProgrammingError: (asyncmy.errors.ProgrammingError) 1045
```

**Solution:**
```powershell
# Check MySQL is running
# Verify credentials in Database.py:
# - Username: root
# - Password: Nilesh@143
# - Host: localhost
# - Port: 3306
# - Database: super_clinic

# Test connection:
mysql -u root -pNilesh@143 -h localhost -e "SELECT 1;"
```

### Issue 3: OpenAI API Error

```
AuthenticationError: Incorrect API key provided
```

**Solution:**
1. Verify your API key at https://platform.openai.com/account/api-keys
2. Add it to `.env` file:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
   ```
3. Restart the server

### Issue 4: Port Already in Use

```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solution:**
```powershell
# Use a different port
uvicorn api_server:app --host 0.0.0.0 --port 9000 --reload

# Or kill the process using port 8007:
netstat -ano | findstr :8007
taskkill /PID <PID> /F
```

### Issue 5: Virtual Environment Not Activating

**Solution:**
```powershell
# If execution policy error occurs:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate:
.\venv\Scripts\Activate.ps1

# Or use Command Prompt instead:
venv\Scripts\activate.bat
```

### Issue 6: dist Folder Not Found

```
[WARN] dist directory not found at E:\Projects\DoctorAssistantChatBot\dist
```

**Solution:**
- Ensure the `dist/` folder exists in project root
- If missing, the frontend won't be served, but API will still work
- Access API docs at: http://localhost:8007/docs

### Issue 7: Module Not Found Errors

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print(fastapi.__version__)"
```

---

## 📝 Example Workflow

1. **Start Server:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python api_server.py
   ```

2. **Open Browser:**
   - Go to http://localhost:8007/

3. **Interact with ChatBot:**
   - "Show me all doctors"
   - "I want to book with a cardiologist"
   - "What's available next week?"
   - "Book appointment with Dr. Smith tomorrow at 10:00 AM"

4. **Check API Documentation:**
   - Go to http://localhost:8007/docs (Swagger UI)

---

## 🛠️ Development

### Enable Debug Logging

Edit `api_server.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Hot Reload Development

```powershell
uvicorn api_server:app --host 0.0.0.0 --port 8007 --reload
```

### Test Database Queries

```powershell
python -c "
from Database import engine, get_async_session
import asyncio

async def test():
    async with get_async_session() as session:
        from EntityClasses import Doctor
        from sqlalchemy.future import select
        result = await session.execute(select(Doctor))
        doctors = result.scalars().all()
        print(f'Found {len(doctors)} doctors')

asyncio.run(test())
"
```

---

## 📚 API Functions Supported by AI

The chatbot can understand and call these backend functions:

1. **get_doctors** - List all doctors
2. **filter_doctors** - Filter doctors by specialty (with fuzzy matching)
3. **get_doctor_availability** - Get available slots (optional date parameter)
4. **book_appointment** - Book an appointment
5. **recommend_alternatives** - Get alternative slots if unavailable

---

## 🚢 Production Deployment

### Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8007"]
```

Run:
```bash
docker build -t doctor-chatbot .
docker run -p 8007:8007 -e OPENAI_API_KEY=YOUR_KEY doctor-chatbot
```

### Environment Variables for Production

```env
OPENAI_API_KEY=your-production-key
DATABASE_URL=mysql+asyncmy://prod_user:prod_password@prod_host:3306/super_clinic
PORT=8007
HOST=0.0.0.0
```

### CORS for Production

Edit `api_server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## 📞 Support & Contributions

For issues or feature requests, please:
1. Check the Troubleshooting section
2. Review the database schema in `EntityClasses.py`
3. Check OpenAI API documentation

---

## 📄 License

This project is part of the Super Clinic Assistant system.

---

## ✅ Checklist Before Running

- [ ] Python 3.9+ installed
- [ ] MySQL 8.0+ installed and running
- [ ] Virtual environment created (`venv`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database created and seeded with sample data
- [ ] OpenAI API key obtained and added to `.env`
- [ ] Database credentials verified in `Database.py`
- [ ] Port 8007 is available
- [ ] `dist/` folder exists with frontend files

---

**Happy Coding! 🚀**

