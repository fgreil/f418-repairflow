from flask import Flask, jsonify
from pymongo import MongoClient
from datetime import datetime
import subprocess

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['repair_shop']  # Database name

@app.route('/')
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':  # Skip static files
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                'path': str(rule)
            })
    return jsonify({'available_endpoints': sorted(routes, key=lambda x: x['path'])})


@app.route("/sorry")
def get_excuse():
    try:
       result = subprocess.run(['/usr/games/fortune'], capture_output=True, text=True, timeout=5 )
       excuse = result.stdout.strip()

       # Remove "BOFH excuse #XXX:" prefix if present
       if excuse.startswith("BOFH excuse"):
           # Find the position after the newlines following the prefix
           lines = excuse.split('\n', 2)  # Split at most into 3 parts
           if len(lines) >= 3:
              excuse = lines[2].strip()  # Take everything after the second newline
           elif len(lines) == 2:
              excuse = lines[1].strip()  # Take everything after the first newline

       return jsonify({"excuse": excuse})
    except subprocess.TimeoutExpired:
       return jsonify({"excuse": "The excuse generator timed out"}), 500
    except FileNotFoundError:
       return jsonify({"excuse": "Command not found"}), 500
    except Exception as e:
       return jsonify({"excuse": "Error: {str(e)}"}), 500
