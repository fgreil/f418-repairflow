from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta, time
from bson.decimal128 import Decimal128
import subprocess
import logging
import calendar

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

# Appointment booking configuration
SLOT_DURATION_MINUTES = 30
WORKING_HOURS = {
    0: (time(9, 0), time(16, 0)),   # Monday
    1: (time(9, 0), time(16, 0)),   # Tuesday
    2: (time(9, 0), time(16, 0)),   # Wednesday
    3: (time(9, 0), time(16, 0)),   # Thursday
    4: (time(9, 0), time(16, 0)),   # Friday
    5: (time(10, 0), time(15, 0)),  # Saturday
    6: None  # Sunday - closed
}
FIXED_HOLIDAYS = [
    (5, 1),    # May 1st
    (10, 3),   # October 3rd
    (12, 25),  # December 25th
    (12, 26)   # December 26th
]

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


# Helper functions for appointment booking
def is_working_day(date):
    """Check if a date is a working day"""
    # Check if it's a weekday we work on
    if date.weekday() not in WORKING_HOURS or WORKING_HOURS[date.weekday()] is None:
        return False
    
    # Check if it's a holiday
    if (date.month, date.day) in FIXED_HOLIDAYS:
        return False
    
    return True


def generate_slots_for_day(date):
    """Generate all possible time slots for a given day"""
    if not is_working_day(date):
        return []
    
    start_time, end_time = WORKING_HOURS[date.weekday()]
    slots = []
    
    current_time = datetime.combine(date, start_time)
    end_datetime = datetime.combine(date, end_time)
    
    while current_time < end_datetime:
        slots.append(current_time)
        current_time += timedelta(minutes=SLOT_DURATION_MINUTES)
    
    return slots


def get_date_range(period):
    """Get start and end dates for a given period"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == "this_week":
        # Start from Monday of current week
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "next_week":
        # Start from Monday of next week
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        end = start + timedelta(days=6)
    elif period == "this_month":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
    elif period == "next_month":
        if today.month == 12:
            start = datetime(today.year + 1, 1, 1)
            last_day = calendar.monthrange(start.year, start.month)[1]
        else:
            start = datetime(today.year, today.month + 1, 1)
            last_day = calendar.monthrange(start.year, start.month)[1]
        end = start.replace(day=last_day)
    elif period == "this_year":
        start = datetime(today.year, 1, 1)
        end = datetime(today.year, 12, 31)
    else:
        return None, None
    
    return start, end


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
        'GET /slots?period=<period>': {
            'description': 'Get available appointment slots',
            'parameters': 'period: this_week, next_week, this_month, next_month, this_year',
            'returns': 'List of available appointment slots'
        },
        'GET /slot?id=<id>': {
            'description': 'Get details of a specific appointment',
            'parameters': 'id (required): MongoDB ObjectId of the appointment',
            'returns': 'Complete appointment document'
        },
        'POST /slot': {
            'description': 'Update or cancel an appointment',
            'required_fields': ['id'],
            'optional_fields': ['status', 'datetime'],
            'returns': 'Update confirmation'
        },
        'GET /appointments': {
            'description': 'Get all appointments with full details (admin view)',
            'parameters': 'status (optional), start_date (optional), end_date (optional)',
            'returns': 'List of all appointments'
        },
        'GET /sorry': {
            'description': 'Get a random BOFH excuse',
            'returns': 'Random excuse text'
        }
    }
    
    return jsonify({
        'api_name': 'Repair Flow API',
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
            
            # Convert appointment history datetimes
            if 'appointmentHistory' in repair_request:
                for hist in repair_request['appointmentHistory']:
                    if 'appointmentId' in hist:
                        hist['appointmentId'] = str(hist['appointmentId'])
                    if 'datetime' in hist:
                        hist['datetime'] = hist['datetime'].isoformat()
                    if 'actionAt' in hist:
                        hist['actionAt'] = hist['actionAt'].isoformat()
            
            if 'currentAppointment' in repair_request and repair_request['currentAppointment']:
                if 'appointmentId' in repair_request['currentAppointment']:
                    repair_request['currentAppointment']['appointmentId'] = str(repair_request['currentAppointment']['appointmentId'])
                if 'datetime' in repair_request['currentAppointment']:
                    repair_request['currentAppointment']['datetime'] = repair_request['currentAppointment']['datetime'].isoformat()
            
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
                for repair in data['repairs']:
                    if 'quotedPrice' in repair:
                       repair['quotedPrice'] = Decimal128(str(repair['quotedPrice']))
                repair_request['repairs'] = data['repairs']
            if 'status' in data:
                repair_request['status'] = data['status']
            if 'totalQuotedPrice' in data:
                repair_request['totalQuotedPrice'] = data['totalQuotedPrice']
            if 'totalActualPrice' in data:
                repair_request['totalActualPrice'] = data['totalActualPrice']
            if 'additionalNotes' in data:
                repair_request['additionalNotes'] = data['additionalNotes']
            
            # Handle appointment if provided
            appointment_datetime = None
            if 'appointment' in data:
                # Convert date string to datetime object for MongoDB
                appointment = data['appointment'].copy()
                if 'date' in appointment and isinstance(appointment['date'], str):
                    # Parse date string (format: YYYY-MM-DD)
                    from datetime import datetime as dt
                    appointment_datetime = dt.strptime(appointment['date'], '%Y-%m-%d')
                    appointment['date'] = appointment_datetime
                repair_request['appointment'] = appointment
            
            logger.info(f"Inserting into MongoDB: {repair_request}")
            # Insert into MongoDB
            result = db.repair_requests.insert_one(repair_request)
            logger.info(f"Successfully inserted with ID: {result.inserted_id}")
            
            # Create appointment document if appointment data was provided
            if appointment_datetime:
                appointment_doc = {
                    'datetime': appointment_datetime,
                    'status': 'booked',
                    'requestId': result.inserted_id,
                    'customer': {
                        'name': data['customer'].get('name', ''),
                        'email': data['customer'].get('email', ''),
                        'phone': data['customer'].get('phone', '')
                    },
                    'device': {
                        'brand': data['device'].get('brand', ''),
                        'model': data['device'].get('model', ''),
                        'color': data['device'].get('color', ''),
                        'imei': data['device'].get('imei', '')
                    },
                    'createdAt': datetime.utcnow(),
                    'updatedAt': datetime.utcnow()
                }
                
                appt_result = db.appointments.insert_one(appointment_doc)
                logger.info(f"Created appointment with ID: {appt_result.inserted_id}")
                
                # Update repair request with appointment reference
                db.repair_requests.update_one(
                    {'_id': result.inserted_id},
                    {'$set': {
                        'currentAppointment': {
                            'appointmentId': appt_result.inserted_id,
                            'datetime': appointment_datetime,
                            'status': 'booked'
                        },
                        'appointmentHistory': [{
                            'appointmentId': appt_result.inserted_id,
                            'datetime': appointment_datetime,
                            'status': 'booked',
                            'action': 'booked',
                            'actionAt': datetime.utcnow()
                        }]
                    }}
                )
            
            response_data = {
                'success': True,
                'id': str(result.inserted_id),
                'message': 'Repair request created successfully',
                'submittedAt': repair_request['submittedAt'].isoformat()
            }
            
            if appointment_datetime:
                response_data['appointmentId'] = str(appt_result.inserted_id)
                response_data['appointmentDatetime'] = appointment_datetime.isoformat()
            
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


@app.route("/slots", methods=['GET'])
def list_available_slots():
    """Get available appointment slots for a specified period"""
    try:
        period = request.args.get('period', 'this_week')
        
        start_date, end_date = get_date_range(period)
        if start_date is None:
            return jsonify({
                'success': False,
                'error': 'Invalid period. Use: this_week, next_week, this_month, next_month, or this_year'
            }), 400
        
        # Get all booked appointments in this date range
        booked_slots = db.appointments.find({
            'datetime': {
                '$gte': start_date,
                '$lte': end_date
            },
            'status': {'$in': ['booked', 'confirmed']}
        })
        
        booked_datetimes = {appt['datetime'] for appt in booked_slots}
        
        # Generate all possible slots
        available_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            day_slots = generate_slots_for_day(current_date)
            
            for slot_time in day_slots:
                if slot_time >= datetime.now() and slot_time not in booked_datetimes:
                    available_slots.append({
                        'datetime': slot_time.isoformat(),
                        'date': slot_time.strftime('%Y-%m-%d'),
                        'time': slot_time.strftime('%H:%M'),
                        'day_of_week': slot_time.strftime('%A')
                    })
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'count': len(available_slots),
            'slots': available_slots
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing slots: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/slot", methods=['GET', 'POST'])
def handle_slot():
    """Get details or update/cancel an appointment slot"""
    if request.method == 'GET':
        try:
            slot_id = request.args.get('id')
            if not slot_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing id parameter'
                }), 400
            
            from bson.objectid import ObjectId
            appointment = db.appointments.find_one({'_id': ObjectId(slot_id)})
            
            if not appointment:
                return jsonify({
                    'success': False,
                    'error': 'Appointment not found'
                }), 404
            
            # Convert ObjectId and datetime for JSON
            appointment['_id'] = str(appointment['_id'])
            appointment['datetime'] = appointment['datetime'].isoformat()
            if 'requestId' in appointment:
                appointment['requestId'] = str(appointment['requestId'])
            if 'createdAt' in appointment:
                appointment['createdAt'] = appointment['createdAt'].isoformat()
            if 'updatedAt' in appointment:
                appointment['updatedAt'] = appointment['updatedAt'].isoformat()
            
            return jsonify({
                'success': True,
                'data': appointment
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting slot: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    else:  # POST - update or cancel
        try:
            data = request.get_json()
            slot_id = data.get('id')
            
            if not slot_id:
                return jsonify({
                    'success': False,
                    'error': 'Missing id field'
                }), 400
            
            from bson.objectid import ObjectId
            
            # Get current appointment
            current_appt = db.appointments.find_one({'_id': ObjectId(slot_id)})
            if not current_appt:
                return jsonify({
                    'success': False,
                    'error': 'Appointment not found'
                }), 404
            
            update_data = {'updatedAt': datetime.utcnow()}
            action = None
            new_datetime = None
            
            if 'status' in data:
                update_data['status'] = data['status']
                if data['status'] == 'cancelled':
                    action = 'cancelled'
            
            if 'datetime' in data:
                # Parse new datetime
                new_datetime = datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
                update_data['datetime'] = new_datetime
                action = 'rescheduled'
            
            result = db.appointments.update_one(
                {'_id': ObjectId(slot_id)},
                {'$set': update_data}
            )
            
            if result.matched_count == 0:
                return jsonify({
                    'success': False,
                    'error': 'Appointment not found'
                }), 404
            
            # Update repair request appointment history if there's an action
            if action and 'requestId' in current_appt:
                history_entry = {
                    'appointmentId': ObjectId(slot_id),
                    'datetime': new_datetime if new_datetime else current_appt['datetime'],
                    'status': update_data.get('status', current_appt['status']),
                    'action': action,
                    'actionAt': datetime.utcnow()
                }
                
                update_fields = {
                    '$push': {'appointmentHistory': history_entry}
                }
                
                # Update current appointment if not cancelled
                if action != 'cancelled':
                    update_fields['$set'] = {
                        'currentAppointment': {
                            'appointmentId': ObjectId(slot_id),
                            'datetime': new_datetime if new_datetime else current_appt['datetime'],
                            'status': update_data.get('status', current_appt['status'])
                        }
                    }
                else:
                    update_fields['$set'] = {'currentAppointment': None}
                
                db.repair_requests.update_one(
                    {'_id': current_appt['requestId']},
                    update_fields
                )
            
            return jsonify({
                'success': True,
                'message': 'Appointment updated successfully',
                'modified_count': result.modified_count
            }), 200
            
        except Exception as e:
            logger.error(f"Error updating slot: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@app.route("/appointments", methods=['GET'])
def list_all_appointments():
    """Get all appointments with full details (admin view)"""
    try:
        # Optional filters
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = {}
        
        if status:
            query['status'] = status
        
        if start_date or end_date:
            query['datetime'] = {}
            if start_date:
                query['datetime']['$gte'] = datetime.fromisoformat(start_date)
            if end_date:
                query['datetime']['$lte'] = datetime.fromisoformat(end_date)
        
        appointments = list(db.appointments.find(query).sort('datetime', 1))
        
        # Convert ObjectId and datetime for JSON
        for appt in appointments:
            appt['_id'] = str(appt['_id'])
            appt['datetime'] = appt['datetime'].isoformat()
            if 'requestId' in appt:
                appt['requestId'] = str(appt['requestId'])
            if 'createdAt' in appt:
                appt['createdAt'] = appt['createdAt'].isoformat()
            if 'updatedAt' in appt:
                appt['updatedAt'] = appt['updatedAt'].isoformat()
        
        return jsonify({
            'success': True,
            'count': len(appointments),
            'appointments': appointments
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing appointments: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == "__main__":
    # Run the Flask development server
    # For production, use a proper WSGI server like gunicorn
    app.run(host="0.0.0.0", port=5001, debug=True)
