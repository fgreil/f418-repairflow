from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson.decimal128 import Decimal128
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS with explicit configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Add request logging middleware
@app.before_request
def log_request():
    logger.info(f"Request: {request.method} {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.method == 'POST':
        logger.info(f"Body: {request.get_data(as_text=True)}")

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['repair_shop']  # Database name

@app.route('/')
def list_routes():
    # Custom endpoint documentation
    endpoints = {
        'GET /': {
            'description': 'API documentation (this page)'
        },
        'GET /requests': {
            'description': 'List all repair request IDs',
            'returns': 'Array of all repair request IDs'
        },
        'GET /request?id=<id>': {
            'description': 'Get details of a specific repair request',
            'parameters': 'id (required): MongoDB ObjectId of the repair request',
            'returns': 'Complete repair request document'
        },
        'POST /request': {
            'description': 'Create a new repair request',
            'required_fields': ['customer', 'device', 'serviceType'],
            'optional_fields': ['repairs', 'appointment', 'status', 'totalQuotedPrice', 'totalActualPrice', 'additionalNotes'],
            'returns': 'ID of newly created repair request'
        },
        'GET /sorry': {
            'description': 'Get a random BOFH excuse',
            'returns': 'Random excuse text'
        }
    }
    
    return jsonify({
        'api_name': 'Repair Shop API',
        'version': '1.0',
        'endpoints': endpoints
    })


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


@app.route("/requests", methods=['GET'])
def list_repair_requests():
    try:
        # Get all repair requests but only return their IDs
        repair_requests = db.repair_requests.find({}, {'_id': 1})
        ids = [str(doc['_id']) for doc in repair_requests]
        
        return jsonify({
            'success': True,
            'count': len(ids),
            'ids': ids
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/request", methods=['GET', 'POST'])
def handle_repair_request():
    if request.method == 'GET':
        # Get repair request by ID
        try:
            request_id = request.args.get('id')
            if not request_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing id parameter'
                }), 400
            
            from bson.objectid import ObjectId
            
            # Find the repair request by ID
            repair_request = db.repair_requests.find_one({'_id': ObjectId(request_id)})
            
            if not repair_request:
                return jsonify({
                    'success': False,
                    'error': 'Repair request not found'
                }), 404
            
            # Convert ObjectId to string for JSON serialization
            repair_request['_id'] = str(repair_request['_id'])
            
            # Convert datetime objects to ISO format strings
            if 'submittedAt' in repair_request:
                repair_request['submittedAt'] = repair_request['submittedAt'].isoformat()
            if 'updatedAt' in repair_request:
                repair_request['updatedAt'] = repair_request['updatedAt'].isoformat()
            
            return jsonify({
                'success': True,
                'data': repair_request
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    else:  # POST method
        try:
            logger.info("POST /request - Processing repair request submission")
            data = request.get_json()
            logger.info(f"Received data: {data}")
            
            # Create repair request document with required fields
            repair_request = {
                'customer': data['customer'],
                'device': data['device'],
                'serviceType': data['serviceType'],
                'submittedAt': datetime.utcnow()
            }
            
            # Add optional fields if provided
            if 'repairs' in data:
                if 'repairs' in data:
                    for repair in data['repairs']:
                        if 'quotedPrice' in repair:
                           repair['quotedPrice'] = Decimal128(str(repair['quotedPrice']))
                repair_request['repairs'] = data['repairs']
            if 'appointment' in data:
                # Convert date string to datetime object for MongoDB
                appointment = data['appointment'].copy()
                if 'date' in appointment and isinstance(appointment['date'], str):
                    # Parse date string (format: YYYY-MM-DD)
                    from datetime import datetime as dt
                    appointment['date'] = dt.strptime(appointment['date'], '%Y-%m-%d')
                repair_request['appointment'] = appointment
            if 'status' in data:
                repair_request['status'] = data['status']
            if 'totalQuotedPrice' in data:
                repair_request['totalQuotedPrice'] = data['totalQuotedPrice']
            if 'totalActualPrice' in data:
                repair_request['totalActualPrice'] = data['totalActualPrice']
            if 'additionalNotes' in data:
                repair_request['additionalNotes'] = data['additionalNotes']
            
            logger.info(f"Inserting into MongoDB: {repair_request}")
            # Insert into MongoDB
            result = db.repair_requests.insert_one(repair_request)
            logger.info(f"Successfully inserted with ID: {result.inserted_id}")
            
            response_data = {
                'success': True,
                'id': str(result.inserted_id),
                'message': 'Repair request created successfully',
                'submittedAt': repair_request['submittedAt'].isoformat()
            }
            logger.info(f"Sending response: {response_data}")
            
            return jsonify(response_data), 201
            
        except KeyError as e:
            logger.error(f"Missing required field: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Missing required field: {str(e)}'
            }), 400
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500



if __name__ == "__main__":
    # Run the Flask development server
    # For production, use a proper WSGI server like gunicorn
    app.run(host="0.0.0.0", port=5001, debug=True)
