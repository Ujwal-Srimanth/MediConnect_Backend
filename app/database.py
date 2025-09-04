import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGODB_URI, DB_NAME


client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())


def get_collection(db_name: str = DB_NAME, collection_name: str = "demo"):
    db = client[db_name]
    return db[collection_name]

def get_database(db_name: str = DB_NAME):
    return client[db_name]

# default usage (from .env)
patients_collection = get_collection(db_name="Patient_Appointment",collection_name="Patients_Table")
users_collection = get_collection(db_name="Patient_Appointment",collection_name="users")
otps_collection = get_collection(db_name="Patient_Appointment",collection_name="otp_store")
database = get_database()

