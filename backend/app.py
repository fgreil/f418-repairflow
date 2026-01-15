# ============================================================================
# IMPORTS
# ============================================================================

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, time, timedelta
from bson.decimal128 import Decimal128
import subprocess
import logging
from icalendar import Calendar, Event
from functools import wraps

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

# Enable CORS with explicit configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ============================================================================
# APPOINTMENT BOOKING CONFIGURATION
# ============================================================================

# Appointment booking configuration
SLOT_DURATION_MINUTES = 30  # to be used later for the endpoint /slot with method POST
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

# Calendar credentials (you should change these!)
CALENDAR_USERNAME = "admin"
CALENDAR_PASSWORD = "change_me_please"

# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

# Add request logging middleware
@app.before_request
def log_request():
    logger.info(f"Request: {request.method} {request.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.method == 'POST':
        logger.info(f"Body: {request.get_data(as_text=True)}")

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['repair_shop']  # Database name

# ============================================================================
# AUTHENTICATION
# ============================================================================

# Authentication decorator for protected calendar endpoint
def require_calendar_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != CALENDAR_USERNAME or auth.password != CALENDAR_PASSWORD:
            return Response(
                'Authentication required for full calendar access',
                401,
                {'WWW-Authenticate': 'Basic realm="Calendar Access"'}
            )
        return f(*args, **kwargs)
    return decorated

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_holiday(date_obj):
    """Check if a date is a configured holiday"""
    return (date_obj.month, date_obj.day) in FIXED_HOLIDAYS


def is_working_day(date_obj):
    """Check if a date is a working day (has working hours and not a holiday)"""
    weekday = date_obj.weekday()
    return WORKING_HOURS.get(weekday) is not None and not is_holiday(date_obj)


def get_non_working_blocks(start_date, end_date):
    """
    Generate non-working time blocks (before/after working hours, weekends, holidays)
    Returns list of (start_datetime, end_datetime) tuples
    """
    blocks = []
    current_date = start_date.date()
    end = end_date.date()
    
    while current_date <= end:
        weekday = current_date.weekday()
        working_hours = WORKING_HOURS.get(weekday)
        
        if working_hours is None or is_holiday(current_date):
            # Full day blocked (Sunday or holiday)
            blocks.append((
                datetime.combine(current_date, time(0, 0)),
                datetime.combine(current_date, time(23, 59, 59))
            ))
        else:
            # Block time before working hours
            work_start, work_end = working_hours
            if work_start > time(0, 0):
                blocks.append((
                    datetime.combine(current_date, time(0, 0)),
                    datetime.combine(current_date, work_start)
                ))
            
            # Block time after working hours
            if work_end < time(23, 59, 59):
                blocks.append((
                    datetime.combine(current_date, work_end),
                    datetime.combine(current_date, time(23, 59, 59))
                ))
        
        current_date += timedelta(days=1)
    
    return blocks


def get_appointments(start_date=None, end_date=None):
    """
    Retrieve appointments from MongoDB
    Returns list of appointment dictionaries
    """
    query = {}
    
    # Filter by date range if provided
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter['$gte'] = start_date
        if end_date:
            date_filter['$lte'] = end_date
        query['appointment.date'] = date_filter
    
    # Only get repair requests that have appointments scheduled
    query['appointment'] = {'$exists': True}
    
    appointments = []
    for request_doc in db.repair_requests.find(query):
        if 'appointment' in request_doc:
            appt = request_doc['appointment']
            appointments.append({
                'id': str(request_doc['_id']),
                'customer': request_doc.get('customer', {}),
                'device': request_doc.get('device', {}),
                'service_type': request_doc.get('serviceType', 'Unknown'),
                'date': appt.get('date'),
                'time_slot': appt.get('timeSlot', 'Not specified'),
                'status': request_doc.get('status', 'pending'),
                'notes': request_doc.get('additionalNotes', '')
            })
    
    return appointments

# ============================================================================
# ROUTE HANDLERS - DOCUMENTATION
# ============================================================================

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
        },
        'GET /calendar': {
            'description': 'Full calendar with appointment details as JSON (requires authentication)',
            'authentication': 'HTTP Basic Auth required',
            'returns': 'JSON with complete appointment information'
        },
        'GET /calendar.ics': {
            'description': 'Full calendar with appointment details (requires authentication)',
            'authentication': 'HTTP Basic Auth required',
            'returns': 'iCalendar file with complete appointment information'
        },
        'GET /slots?range=<range>': {
            'description': 'Available/busy slots without details (public)',
            'parameters': 'range (optional): today (default), this_week, next_week, this_month, next_month, this_year',
            'returns': 'JSON with booked slots and non-working hours'
        },
        'GET /slots.ics': {
            'description': 'Available/busy slots as calendar (public)',
            'returns': 'iCalendar file showing busy/free times without details'
        }
    }
    
    return jsonify({
        'api_name': 'Repair Shop API',
        'version': '1.0',
        'endpoints': endpoints
    })

# ============================================================================
# ROUTE HANDLERS - UTILITY ENDPOINTS
# ============================================================================

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

# ============================================================================
# ROUTE HANDLERS - REPAIR REQUESTS
# ============================================================================

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

# ============================================================================
# ROUTE HANDLERS - CALENDAR ENDPOINTS
# ============================================================================

@app.route("/calendar", methods=['GET'])
@require_calendar_auth
def calendar_json():
    """
    Full calendar with all appointment details - JSON format (requires authentication)
    """
    try:
        # Get date range (next 90 days)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=90)
        
        # Get non-working blocks
        non_working_blocks = get_non_working_blocks(start_date, end_date)
        
        # Get appointments with full details
        appointments = get_appointments(start_date, end_date)
        
        # Build response
        events = []
        
        # Add non-working blocks
        for block_start, block_end in non_working_blocks:
            reason = 'Non-working hours'
            if is_holiday(block_start):
                reason = 'Holiday - Shop Closed'
            elif WORKING_HOURS.get(block_start.weekday()) is None:
                reason = 'Weekend - Shop Closed'
            
            events.append({
                'type': 'closed',
                'summary': 'Closed',
                'start': block_start.isoformat(),
                'end': block_end.isoformat(),
                'description': reason
            })
        
        # Add appointments with full details
        for appt in appointments:
            customer_name = f"{appt['customer'].get('firstName', '')} {appt['customer'].get('lastName', '')}".strip()
            device_info = f"{appt['device'].get('manufacturer', '')} {appt['device'].get('model', '')}".strip()
            
            appt_date = appt['date']
            if isinstance(appt_date, datetime):
                events.append({
                    'type': 'appointment',
                    'id': appt['id'],
                    'summary': f"{appt['service_type']}: {customer_name}",
                    'start': appt_date.isoformat(),
                    'end': (appt_date + timedelta(minutes=SLOT_DURATION_MINUTES)).isoformat(),
                    'customer': {
                        'name': customer_name,
                        'phone': appt['customer'].get('phone', 'N/A'),
                        'email': appt['customer'].get('email', 'N/A')
                    },
                    'device': device_info,
                    'service_type': appt['service_type'],
                    'status': appt['status'],
                    'notes': appt['notes']
                })
        
        return jsonify({
            'success': True,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'slot_duration_minutes': SLOT_DURATION_MINUTES,
            'events': events
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating calendar JSON: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/calendar.ics", methods=['GET'])
@require_calendar_auth
def calendar_full():
    """
    Full calendar with all appointment details - requires authentication
    """
    try:
        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//Repair Shop Calendar//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('x-wr-calname', 'Repair Shop - Full Details')
        cal.add('x-wr-timezone', 'UTC')
        
        # Get date range (next 90 days)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=90)
        
        # Add non-working hour blocks
        non_working_blocks = get_non_working_blocks(start_date, end_date)
        for block_start, block_end in non_working_blocks:
            event = Event()
            event.add('summary', 'Closed')
            event.add('dtstart', block_start)
            event.add('dtend', block_end)
            event.add('transp', 'OPAQUE')  # Show as busy
            event.add('status', 'CONFIRMED')
            
            # Add description for closed periods
            if is_holiday(block_start):
                event.add('description', 'Holiday - Shop Closed')
            elif WORKING_HOURS.get(block_start.weekday()) is None:
                event.add('description', 'Weekend - Shop Closed')
            else:
                event.add('description', 'Non-working hours')
            
            cal.add_component(event)
        
        # Add appointments with full details
        appointments = get_appointments(start_date, end_date)
        
        for appt in appointments:
            event = Event()
            
            # Build detailed summary
            customer_name = f"{appt['customer'].get('firstName', '')} {appt['customer'].get('lastName', '')}".strip()
            device_info = f"{appt['device'].get('manufacturer', '')} {appt['device'].get('model', '')}".strip()
            
            event.add('summary', f"{appt['service_type']}: {customer_name}")
            
            # Build detailed description
            description_parts = [
                f"Customer: {customer_name}",
                f"Phone: {appt['customer'].get('phone', 'N/A')}",
                f"Email: {appt['customer'].get('email', 'N/A')}",
                f"Device: {device_info}",
                f"Service: {appt['service_type']}",
                f"Status: {appt['status']}"
            ]
            
            if appt['notes']:
                description_parts.append(f"Notes: {appt['notes']}")
            
            event.add('description', '\n'.join(description_parts))
            
            # Set date/time
            appt_date = appt['date']
            if isinstance(appt_date, datetime):
                event.add('dtstart', appt_date)
                # Assume 30-minute slots by default
                event.add('dtend', appt_date + timedelta(minutes=SLOT_DURATION_MINUTES))
            
            event.add('status', 'CONFIRMED')
            event.add('transp', 'OPAQUE')  # Show as busy
            event.add('uid', f"repair-{appt['id']}@repairshop.local")
            
            cal.add_component(event)
        
        return Response(
            cal.to_ical(),
            mimetype='text/calendar',
            headers={
                'Content-Disposition': 'attachment; filename=repair-shop-full.ics'
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating full calendar: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/slots", methods=['GET'])
def slots_json():
    """
    Public endpoint showing busy/free slots without details - JSON format
    """
    try:
        # Get time range parameter (default: today)
        range_param = request.args.get('range', 'today').lower()
        
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate end_date based on range parameter
        if range_param == 'today':
            end_date = start_date.replace(hour=23, minute=59, second=59)
        elif range_param == 'this_week':
            # End of current week (Sunday)
            days_until_sunday = 6 - start_date.weekday()
            end_date = start_date + timedelta(days=days_until_sunday, hours=23, minutes=59, seconds=59)
        elif range_param == 'next_week':
            # Start of next week (Monday)
            days_until_monday = 7 - start_date.weekday()
            start_date = start_date + timedelta(days=days_until_monday)
            # End of next week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif range_param == 'this_month':
            # End of current month
            if start_date.month == 12:
                end_date = start_date.replace(day=31, hour=23, minute=59, second=59)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
                end_date = next_month - timedelta(seconds=1)
        elif range_param == 'next_month':
            # Start of next month
            if start_date.month == 12:
                start_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                start_date = start_date.replace(month=start_date.month + 1, day=1)
            # End of next month
            if start_date.month == 12:
                end_date = start_date.replace(day=31, hour=23, minute=59, second=59)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
                end_date = next_month - timedelta(seconds=1)
        elif range_param == 'this_year':
            # End of current year
            end_date = start_date.replace(month=12, day=31, hour=23, minute=59, second=59)
        else:
            # Invalid parameter, default to today
            end_date = start_date.replace(hour=23, minute=59, second=59)
        
        # Get non-working blocks
        non_working_blocks = get_non_working_blocks(start_date, end_date)
        
        # Get appointments (without details)
        appointments = get_appointments(start_date, end_date)
        
        # Build response
        busy_slots = []
        
        # Add non-working blocks
        for block_start, block_end in non_working_blocks:
            busy_slots.append({
                'start': block_start.isoformat(),
                'end': block_end.isoformat(),
                'type': 'closed',
                'reason': 'Non-working hours'
            })
        
        # Add booked appointments (without customer details)
        for appt in appointments:
            appt_date = appt['date']
            if isinstance(appt_date, datetime):
                busy_slots.append({
                    'start': appt_date.isoformat(),
                    'end': (appt_date + timedelta(minutes=SLOT_DURATION_MINUTES)).isoformat(),
                    'type': 'booked',
                    'reason': 'Appointment scheduled'
                })
        
        return jsonify({
            'success': True,
            'range': range_param,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'slot_duration_minutes': SLOT_DURATION_MINUTES,
            'busy_slots': busy_slots,
            'working_hours': {
                day: {
                    'start': hours[0].strftime('%H:%M') if hours else None,
                    'end': hours[1].strftime('%H:%M') if hours else None
                } if hours else None
                for day, hours in WORKING_HOURS.items()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating slots JSON: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route("/slots.ics", methods=['GET'])
def slots_ics():
    """
    Public endpoint showing busy/free slots without details - iCalendar format
    """
    try:
        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//Repair Shop Calendar//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('x-wr-calname', 'Repair Shop - Availability')
        cal.add('x-wr-timezone', 'UTC')
        cal.add('method', 'PUBLISH')
        
        # Get date range (next 90 days)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=90)
        
        # Add non-working hour blocks
        non_working_blocks = get_non_working_blocks(start_date, end_date)
        for block_start, block_end in non_working_blocks:
            event = Event()
            event.add('summary', 'Unavailable')
            event.add('dtstart', block_start)
            event.add('dtend', block_end)
            event.add('transp', 'OPAQUE')  # Show as busy
            event.add('status', 'CONFIRMED')
            event.add('class', 'PUBLIC')
            
            cal.add_component(event)
        
        # Add appointments without details
        appointments = get_appointments(start_date, end_date)
        
        for appt in appointments:
            event = Event()
            event.add('summary', 'Busy')  # Generic title only
            
            # Set date/time
            appt_date = appt['date']
            if isinstance(appt_date, datetime):
                event.add('dtstart', appt_date)
                event.add('dtend', appt_date + timedelta(minutes=SLOT_DURATION_MINUTES))
            
            event.add('status', 'CONFIRMED')
            event.add('transp', 'OPAQUE')  # Show as busy
            event.add('class', 'PUBLIC')
            event.add('uid', f"slot-{appt['id']}@repairshop.local")
            
            # No description, location, or attendee information
            
            cal.add_component(event)
        
        return Response(
            cal.to_ical(),
            mimetype='text/calendar',
            headers={
                'Content-Disposition': 'attachment; filename=repair-shop-slots.ics'
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating slots calendar: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the Flask development server
    # For production, use a proper WSGI server like gunicorn
    app.run(host="0.0.0.0", port=5001, debug=True)
