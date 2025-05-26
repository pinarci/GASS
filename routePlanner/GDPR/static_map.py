import os
import urllib.parse
import webbrowser
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def create_static_map_url(origin, destination, waypoints=None):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"

    # Markers
    markers = [
        f"color:green|label:S|{urllib.parse.quote(origin)}",
        f"color:red|label:D|{urllib.parse.quote(destination)}"
    ]

    if waypoints:
        for i, wp in enumerate(waypoints):
            markers.append(f"color:blue|label:{i+1}|{urllib.parse.quote(wp)}")

    # Waypoints path
    path = f"color:0x0000ff|weight:5|{urllib.parse.quote(origin)}"
    if waypoints:
        for wp in waypoints:
            path += f"|{urllib.parse.quote(wp)}"
    path += f"|{urllib.parse.quote(destination)}"

    # Build full URL
    params = {
        "size": "800x600",
        "markers": markers,
        "path": path,
        "key": API_KEY
    }

    # Flatten parameters for URL
    url = base_url + "&".join(
        f"{k}=" + (v if isinstance(v, str) else "&".join(v))
        if not isinstance(v, list) else
        "&".join([f"{k}={item}" for item in v])
        for k, v in params.items()
    )

    return url

# Example usage
if __name__ == "__main__":
    origin = "Kızılay, Ankara"
    destination = "ODTÜ, Ankara"
    waypoints = ["AŞTİ, Ankara", "Bahçelievler, Ankara"]
    map_url = create_static_map_url(origin, destination, waypoints)
    print("🗺️ Opening static map in browser...")
    webbrowser.open(map_url)
