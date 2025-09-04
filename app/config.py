import os
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import logging

logger = logging.getLogger("uvicorn.error")  # Uvicorn's default logger
logger.setLevel(logging.INFO)

load_dotenv()

ENV = "prod"

MONGODB_URI = None
DB_NAME = None
JWT_SECRET = None
logger.info('hi there')

if ENV == "prod":
    logger.info("🔐 Using production environment variables from Azure Key Vault")



    VAULT_URL = os.getenv("VAULT_URL") 

    if not VAULT_URL:
        raise Exception("❌ VAULT_URL not set for production")

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=VAULT_URL, credential=credential)

    MONGODB_URI = client.get_secret("MONGOURI").value
    DB_NAME = client.get_secret("DBNAME").value
    JWT_SECRET = client.get_secret("JWTSECRET").value
    API_BASE_URL = client.get_secret("APIBASEURL").value
    ACS_CONNECTION_STRING = client.get_secret("ACSCONNECTIONSTRING").value
    SENDER_ADDRESS = client.get_secret("SENDERADDRESS").value

    logger.info(VAULT_URL, MONGODB_URI, DB_NAME, JWT_SECRET, API_BASE_URL, ACS_CONNECTION_STRING, SENDER_ADDRESS)
   


    from azure.storage.blob import BlobServiceClient

    AZURE_STORAGE_CONNECTION_STRING = client.get_secret("AZURESTORAGECONNECTIONSTRING").value
    AZURE_CONTAINER_NAME = client.get_secret("AZURECONTAINERNAME").value
    AZURE_STORAGE_ACCOUNT = client.get_secret("AZURESTORAGEACCOUNT").value
    AZURE_STORAGE_KEY = client.get_secret("AZURESTORAGEKEY").value
    logger.info(AZURE_STORAGE_CONNECTION_STRING, AZURE_CONTAINER_NAME, AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY)
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
    try:
        container_client.create_container()
    except Exception:
        pass  


# Uploads directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
