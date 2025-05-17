import os
from dotenv import load_dotenv
import datetime
import re
import json
import urllib.parse
import webbrowser
import googlemaps
import openrouteservice

# Load .env variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ORS_API_KEY = os.getenv("ORS_API_KEY")  # For ORS usage

if not GOOGLE_MAPS_API_KEY:
    print("❌ Missing GOOGLE_MAPS_API_KEY in .env file.")
    exit()

if not ORS_API_KEY:
    print("⚠️ Warning: ORS_API_KEY not found in .env file. ORS features will be disabled.")

# Initialize clients
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
ors_client = openrouteservice.Client(key=ORS_API_KEY) if ORS_API_KEY else None

def get_user_input():
    origin = input("Enter starting address: ")
    mode = input("Enter travel mode (driving, walking, bicycling, transit): ").strip().lower()
    destination = input("Enter destination address: ")
    waypoints_input = input("Enter intermediate stops separated by semicolons (or leave blank): ").strip()
    waypoints = [point.strip() for point in waypoints_input.split(';') if point.strip()] if waypoints_input else []
    return origin, mode, destination, waypoints

def fetch_gmaps_directions(origin, destination, waypoints, mode):
    now = datetime.datetime.now()
    try:
        directions_result = gmaps.directions(
            origin,
            destination,
            mode=mode,
            waypoints=waypoints if waypoints else None,
            optimize_waypoints=True,
            departure_time=now,
            traffic_model="best_guess"
        )
    except Exception as e:
        print(f"❌ Error fetching directions from Google Maps: {e}")
        return None

    if not directions_result:
        print("❌ No route found on Google Maps.")
        return None

    return directions_result[0]

def print_route_summary(route):
    polyline = route['overview_polyline']['points']
    print("\n🧬 Encoded polyline for Google Maps:")
    print(polyline)

    total_duration = 0
    total_distance = 0

    print("\n🚗 Google Maps Route Summary:\n")

    for i, leg in enumerate(route['legs']):
        print(f"🧩 Leg {i+1}: {leg['start_address']} → {leg['end_address']}")
        duration = leg.get('duration_in_traffic', leg['duration'])
        print(f"🕒 Duration: {duration['text']}")
        print(f"📏 Distance: {leg['distance']['text']}")
        total_duration += duration['value']
        total_distance += leg['distance']['value']
        print("🧭 Steps:")
        for step in leg['steps']:
            instr = re.sub(r'<.*?>', '', step['html_instructions'])
            print(f"  ➡️ {instr} ({step['distance']['text']})")
        print("\n" + "-"*50 + "\n")

    print("✅ Google Maps Final Summary:")
    print(f"🟢 Total estimated time: {round(total_duration / 60)} minutes")
    print(f"🟢 Total distance: {round(total_distance / 1000, 2)} km")

    return total_duration, total_distance

def fetch_ors_directions(origin, destination, waypoints, mode):
    if not ors_client:
        print("❌ ORS client not initialized. Skipping ORS routing.")
        return None

    # Convert addresses to coordinates
    try:
        coords = []
        for address in [origin] + waypoints + [destination]:
            geocode = gmaps.geocode(address)
            if not geocode:
                print(f"❌ Geocoding failed for address: {address}")
                return None
            loc = geocode[0]['geometry']['location']
            coords.append((loc['lng'], loc['lat']))  # ORS expects [lng, lat]
    except Exception as e:
        print(f"❌ Error during geocoding for ORS: {e}")
        return None

    # Map travel mode to ORS profile
    profile_map = {
        "driving": "driving-car",
        "walking": "foot-walking",
        "bicycling": "cycling-regular",
        "transit": "driving-car",  # ORS doesn't support transit, fallback driving
    }
    profile = profile_map.get(mode, "driving-car")

    optimize = True if len(coords) >= 4 else False
    if len(coords) < 2:
        print("❌ Need at least origin and destination for ORS routing.")
        return None

    try:
        ors_response = ors_client.directions(
            coordinates=coords,
            profile=profile,
            format='geojson',
            optimize_waypoints=optimize,
            instructions=True
        )
    except Exception as e:
        print(f"❌ Error fetching directions from ORS: {e}")
        return None

    return ors_response

def print_ors_route_summary(ors_response):
    if not ors_response:
        print("No ORS route to display.")
        return None, None

    features = ors_response['features'][0]
    properties = features['properties']
    segments = properties['segments']

    total_duration = 0
    total_distance = 0

    print("\n🚴 ORS Route Summary:\n")

    for i, seg in enumerate(segments):
        print(f"🧩 Segment {i+1}:")
        print(f"🕒 Duration: {round(seg['duration'] / 60)} minutes")
        print(f"📏 Distance: {round(seg['distance'] / 1000, 2)} km")
        total_duration += seg['duration']
        total_distance += seg['distance']

        print("🧭 Steps:")
        for step in seg['steps']:
            instr = step['instruction']
            dist = round(step['distance'], 0)
            print(f"  ➡️ {instr} ({dist} m)")
        print("\n" + "-"*50 + "\n")

    print("✅ ORS Final Summary:")
    print(f"🟢 Total estimated time: {round(total_duration / 60)} minutes")
    print(f"🟢 Total distance: {round(total_distance / 1000, 2)} km")

    return total_duration, total_distance

def save_route_log(origin, destination, waypoints, mode, route, service="Google Maps"):
    now = datetime.datetime.now()
    if service == "Google Maps":
        total_duration = round(sum(
            leg.get('duration_in_traffic', leg['duration'])['value'] for leg in route['legs']
        ) / 60)
        total_distance = round(sum(leg['distance']['value'] for leg in route['legs']) / 1000, 2)
        legs = []
        for leg in route['legs']:
            leg_data = {
                "from": leg['start_address'],
                "to": leg['end_address'],
                "duration": leg.get('duration_in_traffic', leg['duration'])['text'],
                "distance": leg['distance']['text'],
                "steps": []
            }
            for step in leg['steps']:
                instruction = re.sub(r'<.*?>', '', step['html_instructions'])
                leg_data["steps"].append({
                    "instruction": instruction,
                    "distance": step['distance']['text']
                })
            legs.append(leg_data)

        route_data = {
            "service": service,
            "start": origin,
            "destination": destination,
            "waypoints": waypoints,
            "mode": mode,
            "total_duration_min": total_duration,
            "total_distance_km": total_distance,
            "legs": legs
        }

    elif service == "ORS" and route:
        features = route['features'][0]
        properties = features['properties']
        segments = properties['segments']

        legs = []
        for seg in segments:
            leg_data = {
                "duration": round(seg['duration'] / 60),
                "distance": round(seg['distance'] / 1000, 2),
                "steps": []
            }
            for step in seg['steps']:
                leg_data['steps'].append({
                    "instruction": step['instruction'],
                    "distance": round(step['distance'], 0)
                })
            legs.append(leg_data)

        route_data = {
            "service": service,
            "start": origin,
            "destination": destination,
            "waypoints": waypoints,
            "mode": mode,
            "total_duration_min": round(properties['summary']['duration'] / 60),
            "total_distance_km": round(properties['summary']['distance'] / 1000, 2),
            "legs": legs
        }
    else:
        print("No route data to save.")
        return

    filename = f"route_log_{service.lower().replace(' ', '_')}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(route_data, f, ensure_ascii=False, indent=2)

    print(f"\n📁 {service} route log saved as: {filename}")

def create_static_map_url(origin, destination, waypoints=None):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"

    markers = [
        f"color:green|label:S|{urllib.parse.quote(origin)}",
        f"color:red|label:D|{urllib.parse.quote(destination)}"
    ]

    if waypoints:
        for i, wp in enumerate(waypoints):
            markers.append(f"color:blue|label:{i+1}|{urllib.parse.quote(wp)}")

    path = f"color:0x0000ff|weight:5|{urllib.parse.quote(origin)}"
    if waypoints:
        for wp in waypoints:
            path += f"|{urllib.parse.quote(wp)}"
    path += f"|{urllib.parse.quote(destination)}"

    params = {
        "size": "800x600",
        "markers": markers,
        "path": path,
        "key": GOOGLE_MAPS_API_KEY
    }

    url = base_url + "&".join(
        f"{k}=" + (v if isinstance(v, str) else "&".join(v))
        if not isinstance(v, list) else
        "&".join([f"{k}={item}" for item in v])
        for k, v in params.items()
    )
    return url

def open_google_maps_route(origin, destination, waypoints=None, mode="driving"):
    base_url = "https://www.google.com/maps/dir/?api=1"
    params = {
        "origin": origin,
        "destination": destination,
        "travelmode": mode
    }
    if waypoints:
        params["waypoints"] = "|".join(waypoints)

    url = base_url + "&" + urllib.parse.urlencode(params)
    print("\n🌐 Opening Google Maps route in your browser...")
    webbrowser.open(url)

def main():
    origin, mode, destination, waypoints = get_user_input()

    # Google Maps route
    gmaps_route = fetch_gmaps_directions(origin, destination, waypoints, mode)
    if gmaps_route:
        gmaps_duration, gmaps_distance = print_route_summary(gmaps_route)
        save_route_log(origin, destination, waypoints, mode, gmaps_route, "Google Maps")
    else:
        gmaps_duration = None

    # ORS route
    ors_route = fetch_ors_directions(origin, destination, waypoints, mode)
    if ors_route:
        ors_duration, ors_distance = print_ors_route_summary(ors_route)
        save_route_log(origin, destination, waypoints, mode, ors_route, "ORS")
    else:
        ors_duration = None

    # Compare results if both available
    if gmaps_duration and ors_duration:
        print("\n🔍 Route Duration Comparison:")
        print(f"Google Maps: {round(gmaps_duration / 60)} minutes")
        print(f"ORS: {round(ors_duration / 60)} minutes")

        if gmaps_duration < ors_duration:
            print("\n✅ Google Maps offers the faster route.")
        elif ors_duration < gmaps_duration:
            print("\n✅ ORS offers the faster route.")
        else:
            print("\nℹ️ Both routes have the same duration.")

    # Open Google Maps route in browser for user convenience
    if gmaps_route:
        open_google_maps_route(origin, destination, waypoints, mode)

if __name__ == "__main__":
    main()
