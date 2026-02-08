import os
import json
from flask import Flask, send_from_directory, request, jsonify, make_response

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

@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    # For demo, just check for a token in the Authorization header or cookie
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        # Try cookie (not secure, demo only)
        token = request.cookies.get("authToken")
    if token == "demo-token":
        return jsonify({
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        })
    return jsonify({"error": "Unauthorized"}), 401


# --- DEMO DATA ---
DEMO_LEADS = [
    {"id": "1", "name": "John Doe", "email": "john@example.com", "status": "converted", "created_at": "2026-02-08"},
    {"id": "2", "name": "Jane Smith", "email": "jane@example.com", "status": "contacted", "created_at": "2026-02-07"},
    {"id": "3", "name": "Sam Lee", "email": "sam@example.com", "status": "converted", "created_at": "2026-02-06"}
]
DEMO_CAMPAIGNS = [
    {"id": "1", "name": "Spring Sale", "status": "active", "metrics": {"sent": 100, "opened": 80, "clicked": 20, "converted": 5}},
    {"id": "2", "name": "Winter Promo", "status": "completed", "metrics": {"sent": 200, "opened": 150, "clicked": 50, "converted": 3}}
]
DEMO_WORKFLOWS = [
    {"id": "1", "name": "Welcome Flow", "enabled": True, "status": "active"},
    {"id": "2", "name": "Re-engagement", "enabled": False, "status": "inactive"}
]

# --- DEMO API ENDPOINTS ---
@app.route("/api/leads", methods=["GET"])
def api_leads():
    return jsonify(DEMO_LEADS)

@app.route("/api/campaigns", methods=["GET"])
def api_campaigns():
    return jsonify(DEMO_CAMPAIGNS)

@app.route("/api/workflows", methods=["GET"])
def api_workflows():
    return jsonify(DEMO_WORKFLOWS)

@app.route("/api/health/detailed", methods=["GET"])
def api_health_detailed():
    return jsonify({
        "status": "ok",
        "details": "All systems nominal.",
        "uptime_seconds": 123456,
        "version": "1.0.0",
        "database": {"status": "ok", "details": "Connected"},
        "queue": {"status": "ok", "details": "No backlog"},
        "redis": "ok",
        "queue_depth": 0
    })

@app.route("/api/auth/api-keys", methods=["GET"])
def api_auth_api_keys():
    return jsonify({"keys": ["demo-key-1", "demo-key-2"]})

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
            # --- DEMO API ENDPOINTS ---
        return send_from_directory(app.static_folder, "index.html")
    else:
        print(f"[ERROR] index.html not found at: {index_path}")
        return "index.html not found", 500

if __name__ == "__main__":
    print(f"[DEBUG] Serving frontend from: {FRONTEND_DIST}")
    if not os.path.exists(os.path.join(FRONTEND_DIST, "index.html")):
        print("[ERROR] index.html not found in frontend/dist. Please build the frontend.")
    app.run(host="0.0.0.0", port=8000)


