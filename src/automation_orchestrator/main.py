
import os
from flask import Flask, send_from_directory, request, jsonify

# Compute absolute path to frontend/dist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, '../../frontend/dist'))

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="/")

# --- API ROUTES ---
@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    # Simple hardcoded check for demo purposes
    if username == "admin" and password == "admin123":
        return jsonify({"token": "demo-token", "user": {"username": "admin"}})
    return jsonify({"error": "Invalid credentials"}), 401

# --- STATIC/FRONTEND ROUTES ---

# Serve static files and index.html for SPA
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    print(f"[DEBUG] Request for: {path}")
    # Serve API routes as normal
    if path.startswith("api/"):
        print("[DEBUG] API route, not serving frontend.")
        return "", 404
    # Serve static files if they exist
    file_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.isfile(file_path):
        print(f"[DEBUG] Serving static file: {file_path}")
        return send_from_directory(app.static_folder, path)
    # Otherwise, serve index.html for frontend routing
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        print(f"[DEBUG] Serving index.html from: {index_path}")
        return send_from_directory(app.static_folder, "index.html")
    else:
        print(f"[ERROR] index.html not found at: {index_path}")
        return "index.html not found", 500

if __name__ == "__main__":
    print(f"[DEBUG] Serving frontend from: {FRONTEND_DIST}")
    if not os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        print("[ERROR] index.html not found in frontend/dist. Please build the frontend.")
    app.run(host="0.0.0.0", port=8000)
