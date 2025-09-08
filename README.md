---

## 🟧 **Backend README.md**

```markdown
# MediConnect Backend

The backend of **MediConnect** — a secure and scalable healthcare management system.  
Built with **FastAPI**, deployed on **Azure App Service**, and powered by **CosmosDB (Mongo API)**, **Azure Blob Storage**, and **Azure Communication Services (ACS)**.

---

## 🚀 Features
- **Role-Based Access Control (RBAC)** with **JWT Authentication**:
  - Admin APIs accessible only to admins.
  - Role-specific permissions for Patients, Doctors, and Receptionists.
- **Patients** can fetch appointments, records, and reports.
- **Doctors** can manage appointments and upload prescriptions/reports.
- **Receptionists** can approve or cancel appointments.
- **Admins** can onboard hospitals, doctors, and receptionists.
- **File Storage** via **Azure Blob Storage** (medical reports, prescriptions).
- **Secrets Management** via **Azure Key Vault**.
- **Email Notifications** via **Azure Communication Services (ACS)** (appointment confirmations, rejections, reminders).

---

## 🛠️ Tech Stack
- **FastAPI**
- **CosmosDB (Mongo API)**
- **Azure Blob Storage**
- **Azure Key Vault**
- **Azure Communication Services**
- **JWT Authentication + RBAC**

---

## 📂 Project Structure
backend/
│── app/
│ ├── main.py # Entry point
│ ├── models/ # Database models
│ ├── routes/ # API routes
│ ├── services/ # Business logic
│ ├── utils/ # JWT, helpers
│── requirements.txt


---

## ⚡ Deployment
- Deployed on **Azure App Service (Web App)**.
- Connected to **Azure CosmosDB (Mongo API)**.
- Secrets managed in **Azure Key Vault**.

---

## ▶️ Getting Started

### Prerequisites
- Python 3.9+
- FastAPI, Uvicorn

### Installation
```bash
git clone https://github.com/<your-username>/mediconnect-backend.git
cd mediconnect-backend
pip install -r requirements.txt
uvicorn app.main:app --reload
API will be available at http://127.0.0.1:8000.

🔒 Authentication
JWT-based authentication with role-based access control (RBAC).

Tokens must be included in request headers for all secure routes.

📡 API Docs
FastAPI provides auto-generated interactive API docs:

Swagger UI → http://localhost:8000/docs

ReDoc → http://localhost:8000/redoc

📧 Notifications
Appointment confirmations, reminders, and cancellations are handled through Azure Communication Services (ACS).

