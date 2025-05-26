from dotenv import load_dotenv
import os

load_dotenv("/Users/mustafapinarci/Documents/GDPR/.env")

print("Google Maps Key:", os.getenv("GOOGLE_MAPS_API_KEY"))
print("ORS Key:", os.getenv("ORS_API_KEY"))
