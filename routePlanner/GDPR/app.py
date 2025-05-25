from flask import Flask, request, jsonify, render_template
import os
import datetime
import googlemaps
import requests
from dotenv import load_dotenv   

# Load API keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ORS_API_KEY = os.getenv("ORS_API_KEY")

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def index():
    return render_template("index.html", api_key=GOOGLE_API_KEY)

def get_google_directions(origin, destination, waypoints):
    try:
        directions = gmaps.directions(
            origin,
            destination,
            mode="driving",
            waypoints=waypoints,
            optimize_waypoints=True,
            departure_time=datetime.datetime.now()
        )
        if not directions:
            return None
        polyline = directions[0]['overview_polyline']['points']
        duration = sum(leg['duration']['value'] for leg in directions[0]['legs'])
        return {"source": "google", "polyline": polyline, "duration": duration}
    except Exception as e:
        print(f"Google Maps error: {e}")
        return None

def get_ors_directions(origin, destination, waypoints):
    try:
        coordinates = [origin] + waypoints + [destination] if waypoints else [origin, destination]
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
        data = {
            "coordinates": [],
            "instructions": False,
        
        }

        import openrouteservice
        import geopy
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(user_agent="route_planner")
        for address in coordinates:
            location = geolocator.geocode(address)
            if not location:
                return None
            data["coordinates"].append([location.longitude, location.latitude])

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"ORS error: {response.text}")
            return None

        result = response.json()
        polyline = result['routes'][0]['geometry']
        duration = result['routes'][0]['summary']['duration']
        return {"source": "ors", "polyline": polyline, "duration": duration}
    except Exception as e:
        print(f"ORS error: {e}")
        return None

@app.route("/api/route")
def get_best_route():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    waypoints = request.args.get("waypoints")

    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400

    waypoints_list = [w.strip() for w in waypoints.split(",")] if waypoints else []

    google_route = get_google_directions(origin, destination, waypoints_list)
    ors_route = get_ors_directions(origin, destination, waypoints_list)

    if not google_route and not ors_route:
        return jsonify({"error": "No route found from either API"}), 500

    best_route = min(
        [r for r in [google_route, ors_route] if r],
        key=lambda r: r["duration"]
    )

    return jsonify({
        "source": best_route["source"],
        "polyline": best_route["polyline"],
        "duration_seconds": best_route["duration"]
    })

if __name__ == "__main__":
    app.run(debug=True)
