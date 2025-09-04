from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import patients
from app.routes import auth_routes
from app.routes import doctors
from app.routes import hospital
from app.routes import schedules
from app.routes import appointments
from app.routes import admin
from app.config import UPLOAD_DIR

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError




app = FastAPI(title="Patient API")

# ✅ Global validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(l) for l in err["loc"]])
        msg = err["msg"]
        errors.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=422,
        content={"detail": errors},  # nice readable list
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

# Register routers
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(doctors.router,prefix="/doctors",tags=["Doctors"])
app.include_router(hospital.router,prefix="/hospital",tags=["Hospital"])
app.include_router(schedules.router,prefix="/schedules",tags=["schedule"])
app.include_router(appointments.router,prefix="/appointments", tags=["Appointments"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

