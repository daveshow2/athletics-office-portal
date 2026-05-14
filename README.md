# Jose Rizal University (JRU) Athletics Performance Portal
A professional sports science platform for the **JRU Heavy Bombers Track & Field** team.

## 🚀 Key Features
- **Performance Analytics**: Predictive modeling for peak performance using Linear Regression.
- **Injury Risk Assessment**: Acute:Chronic Workload Ratio (ACWR) decision support system.
- **Athlete Management**: Centralized roster with historical performance and training tracking.
- **Wellness Monitoring**: Integrated Hooper Index tracking (Fatigue, Stress, Soreness, Sleep).
- **Exporting**: One-click CSV/Excel exports for team data and training logs.

## 🛡️ Security & Integrity
The system is built with high data integrity standards:
- **Server-Side Validation**: Every input form (Athlete, Training, Wellness, Results) is strictly validated to prevent corrupted analytics.
- **Data Sanitization**: Prevents XSS and maintains consistent data formatting.
- **Environment Aware**: Secure credential handling via `.env` files.

## 📦 Deployment Ready
Configured for modern cloud platforms (Heroku, Railway, etc.):
- **Production Server**: Configured for `Gunicorn`.
- **Database**: Supports SQLite (local) and PostgreSQL (production).
- **Static Asset Management**: Optimized for high-performance delivery.

## 🛠️ Quick Start Guide

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and configure your `SECRET_KEY`.

### 3. Initialize Data
```bash
python seed.py
```

### 4. Run Application (Development)
```bash
python app.py
```

### 5. Login Credentials
- **Coach Access**: `jru_coach` / `athletics2024`
- **Athlete Access**: Use names (e.g., `johndavepuno`) / `athlete123`

---
*Developed for JRU Athletics Performance & Sports Science Office.*
