from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, time, timedelta
from bson.decimal128 import Decimal128
import subprocess
import logging
from icalendar import Calendar, Event
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

# Calendar credentials (you should change these!)
CALENDAR_USERNAME = "admin"
CALENDAR_PASSWORD = "change_me_please"

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

def convert_decimal128(doc):
    """
    Recursively convert Decimal128 objects to floats in a document for JSON serialization
    """
    if isinstance(doc, dict):
        return {key: convert_decimal128(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [convert_decimal128(item) for item in doc]
    elif isinstance(doc, Decimal128):
        return float(doc.to_decimal())
    else:
        return doc


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


def get_calendar_appointments(start_date=None, end_date=None):
    """
    Retrieve appointments from calendar collection
    Returns list of appointment dictionaries
    """
    query = {}
    
    # Filter by date range if provided
    if start_date or end_date:
        date_filter = {}
        if start_date:
            # Convert to date string for comparison
            date_filter['$gte'] = start_date.strftime('%Y-%m-%d')
        if end_date:
            date_filter['$lte'] = end_date.strftime('%Y-%m-%d')
        query['date'] = date_filter
    
    appointments = []
    for cal_entry in db.calendar.find(query):
        appointments.append({
            'id': cal_entry.get('customer', {}).get('request_id', str(cal_entry['_id'])),
            'date': cal_entry.get('date'),
            'timezone': cal_entry.get('timezone', 'UTC'),
            'start_time': cal_entry.get('start_time'),
            'end_time': cal_entry.get('end_time'),
            'customer': cal_entry.get('customer', {}),
            'device': cal_entry.get('device', {})
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
            'description': 'List and search repair requests with filtering',
            'parameters': {
                'start_date': 'Start date (YYYY-MM-DD, default: today)',
                'end_date': 'End date (YYYY-MM-DD, default: start_date + 90 days)',
                'device_type': 'Filter by device type',
                'brand': 'Filter by manufacturer/brand',
                'model': 'Filter by device model',
                'postal_code': 'Filter by customer postal code',
                'customer_search': 'Search across all customer fields (name, email, phone, address)',
                'limit': 'Max results (default: 10, max: 50)'
            },
            'returns': 'Array of matching repair requests with metadata'
        },
        'GET /options': {
            'description': 'Get available filter options',
            'parameters': {
                'filter': 'Required: device_types, brands, models, postal_codes, cities',
                'device_type': 'For models filter: limit to specific device type',
                'brand': 'For models filter: limit to specific brand'
            },
            'examples': [
                '/options?filter=device_types',
                '/options?filter=models&device_type=smartphone',
                '/options?filter=models&brand=Samsung'
            ],
            'returns': 'List of available options (max 50, sorted)'
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
       return jsonify({"excuse": f"Error: {str(e)}"}), 500

# ============================================================================
# ROUTE HANDLERS - REPAIR REQUESTS
# ============================================================================

@app.route("/requests", methods=['GET'])
def list_repair_requests():
    try:
        import time
        start_time = time.time()
        
        # Build query filter
        query = {}
        
        # (1) Filter by request date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                # Default to today if not provided
                date_filter['$gte'] = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if end_date:
                date_filter['$lte'] = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            else:
                # Default to 90 days from start
                start = date_filter.get('$gte', datetime.now())
                date_filter['$lte'] = start + timedelta(days=90)
            
            query['submittedAt'] = date_filter
        
        # (2) Filter by device type
        device_type = request.args.get('device_type')
        if device_type:
            query['device.type'] = device_type
        
        # (3) Filter by brand (manufacturer)
        brand = request.args.get('brand')
        if brand:
            query['device.manufacturer'] = brand
        
        # (4) Filter by model
        model = request.args.get('model')
        if model:
            query['device.model'] = model
        
        # (5) Search by postal code
        postal_code = request.args.get('postal_code')
        if postal_code:
            query['customer.address.postalCode'] = postal_code
        
        # (6) Search by customer (across multiple fields)
        customer_search = request.args.get('customer_search')
        if customer_search:
            # Create regex pattern for case-insensitive search
            regex_pattern = {'$regex': customer_search, '$options': 'i'}
            query['$or'] = [
                {'customer.firstName': regex_pattern},
                {'customer.lastName': regex_pattern},
                {'customer.email': regex_pattern},
                {'customer.phoneNumber': regex_pattern},
                {'customer.address.street': regex_pattern},
                {'customer.address.postalCode': regex_pattern},
                {'customer.address.city': regex_pattern},
                {'customer.address.houseNumber': regex_pattern}
            ]
        
        # Get limit parameter (default 10, max 50)
        limit = request.args.get('limit', '10')
        try:
            limit = min(int(limit), 50)  # Cap at 50
        except ValueError:
            limit = 10
        
        # Execute query
        repair_requests = list(db.repair_requests.find(query).limit(limit))
        
        # Convert to response format
        results = []
        for doc in repair_requests:
            # Convert Decimal128 to float
            doc = convert_decimal128(doc)
            
            doc['_id'] = str(doc['_id'])
            
            # Convert datetime objects to ISO format
            if 'submittedAt' in doc:
                doc['submittedAt'] = doc['submittedAt'].isoformat()
            if 'updatedAt' in doc:
                doc['updatedAt'] = doc['updatedAt'].isoformat()
            if 'appointment' in doc and 'date' in doc['appointment']:
                if isinstance(doc['appointment']['date'], datetime):
                    doc['appointment']['date'] = doc['appointment']['date'].strftime('%Y-%m-%d')
            
            results.append(doc)
        
        # Calculate search time
        search_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'count': len(results),
            'total_found': db.repair_requests.count_documents(query),
            'limit': limit,
            'search_time_ms': round(search_time * 1000, 2),
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in list_repair_requests: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/options", methods=['GET'])
def get_filter_options():
    """
    Get available filter options for search
    Examples:
    - /options?filter=device_types
    - /options?filter=brands
    - /options?filter=models&device_type=smartphone
    - /options?filter=models&brand=Samsung
    """
    try:
        import time
        start_time = time.time()
        
        filter_type = request.args.get('filter')
        
        if not filter_type:
            return jsonify({
                'success': False,
                'error': 'Missing filter parameter',
                'available_filters': ['device_types', 'brands', 'models', 'postal_codes', 'cities']
            }), 400
        
        results = []
        
        if filter_type == 'device_types':
            # Get all unique device types
            results = db.repair_requests.distinct('device.type')
            
        elif filter_type == 'brands':
            # Get all unique brands/manufacturers
            results = db.repair_requests.distinct('device.manufacturer')
            
        elif filter_type == 'models':
            # Get models, optionally filtered by device_type or brand
            query = {}
            device_type = request.args.get('device_type')
            brand = request.args.get('brand')
            
            if device_type:
                query['device.type'] = device_type
            if brand:
                query['device.manufacturer'] = brand
            
            if query:
                # Use aggregation to get distinct models with filter
                results = db.repair_requests.find(query).distinct('device.model')
            else:
                results = db.repair_requests.distinct('device.model')
        
        elif filter_type == 'postal_codes':
            # Get all unique postal codes
            results = db.repair_requests.distinct('customer.address.postalCode')
            
        elif filter_type == 'cities':
            # Get all unique cities
            results = db.repair_requests.distinct('customer.address.city')
            
        else:
            return jsonify({
                'success': False,
                'error': f'Invalid filter type: {filter_type}',
                'available_filters': ['device_types', 'brands', 'models', 'postal_codes', 'cities']
            }), 400
        
        # Filter out None values and limit to 50 results
        results = [r for r in results if r is not None][:50]
        
        search_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'filter': filter_type,
            'count': len(results),
            'search_time_ms': round(search_time * 1000, 2),
            'options': sorted(results)  # Sort alphabetically for better UX
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_filter_options: {str(e)}", exc_info=True)
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
            
            # Convert Decimal128 to float
            repair_request = convert_decimal128(repair_request)
            
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
            
            # If appointment is provided, also insert into calendar collection
            if 'appointment' in data:
                appointment_data = data['appointment']
                
                # Parse the appointment date and time
                appt_date_str = appointment_data.get('date')  # YYYY-MM-DD
                appt_time_str = appointment_data.get('timeSlot', '09:00')  # HH:MM
                
                # Calculate start and end times
                if ':' in appt_time_str:
                    start_hour, start_minute = map(int, appt_time_str.split(':'))
                else:
                    start_hour, start_minute = 9, 0
                
                end_hour = start_hour
                end_minute = start_minute + SLOT_DURATION_MINUTES
                if end_minute >= 60:
                    end_hour += end_minute // 60
                    end_minute = end_minute % 60
                
                start_time = f"{start_hour:02d}:{start_minute:02d}"
                end_time = f"{end_hour:02d}:{end_minute:02d}"
                
                # Create calendar entry
                calendar_entry = {
                    'date': appt_date_str,
                    'timezone': 'UTC',
                    'start_time': start_time,
                    'end_time': end_time,
                    'customer': {
                        'request_id': str(result.inserted_id),
                        'booking_time': datetime.utcnow().isoformat(),
                        'first_name': data['customer'].get('firstName', ''),
                        'last_name': data['customer'].get('lastName', ''),
                        'email': data['customer'].get('email', ''),
                        'phone': data['customer'].get('phoneNumber', '')
                    },
                    'device': {
                        'device_type': data['device'].get('type', ''),
                        'brand': data['device'].get('manufacturer', ''),
                        'model': data['device'].get('model', '')
                    }
                }
                
                logger.info(f"Inserting into calendar collection: {calendar_entry}")
                db.calendar.insert_one(calendar_entry)
                logger.info("Successfully inserted into calendar collection")
            
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
        
        # Get appointments from calendar collection
        appointments = get_calendar_appointments(start_date, end_date)
        
        # Build response with appointments only
        events = []
        
        for appt in appointments:
            events.append({
                'type': 'appointment',
                'id': appt['id'],
                'date': appt['date'],
                'timezone': appt['timezone'],
                'start': appt['start_time'],
                'end': appt['end_time'],
                'customer': appt['customer'],
                'device': appt['device']
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
        
        # Add appointments with full details from calendar collection
        appointments = get_calendar_appointments(start_date, end_date)
        
        for appt in appointments:
            event = Event()
            
            # Build detailed summary
            customer = appt.get('customer', {})
            device = appt.get('device', {})
            customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            device_info = f"{device.get('brand', '')} {device.get('model', '')}".strip()
            
            event.add('summary', f"Appointment: {customer_name}")
            
            # Build detailed description
            description_parts = [
                f"Customer: {customer_name}",
                f"Phone: {customer.get('phone', 'N/A')}",
                f"Email: {customer.get('email', 'N/A')}",
                f"Device: {device_info}",
                f"Device Type: {device.get('device_type', 'N/A')}"
            ]
            
            event.add('description', '\n'.join(description_parts))
            
            # Set date/time - combine date string with time string
            appt_date_str = appt.get('date')  # YYYY-MM-DD
            start_time_str = appt.get('start_time')  # HH:MM
            end_time_str = appt.get('end_time')  # HH:MM
            
            if appt_date_str and start_time_str:
                # Parse date and time
                appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
                start_hour, start_minute = map(int, start_time_str.split(':'))
                start_datetime = datetime.combine(appt_date, time(start_hour, start_minute))
                
                event.add('dtstart', start_datetime)
                
                if end_time_str:
                    end_hour, end_minute = map(int, end_time_str.split(':'))
                    end_datetime = datetime.combine(appt_date, time(end_hour, end_minute))
                    event.add('dtend', end_datetime)
                else:
                    event.add('dtend', start_datetime + timedelta(minutes=SLOT_DURATION_MINUTES))
            
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
        
        # Get appointments from calendar collection (without customer details)
        appointments = get_calendar_appointments(start_date, end_date)
        
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
            appt_date_str = appt.get('date')  # YYYY-MM-DD
            start_time_str = appt.get('start_time')  # HH:MM
            end_time_str = appt.get('end_time')  # HH:MM
            
            if appt_date_str and start_time_str:
                # Parse date and time to create ISO format datetime
                appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
                start_hour, start_minute = map(int, start_time_str.split(':'))
                start_datetime = datetime.combine(appt_date, time(start_hour, start_minute))
                
                if end_time_str:
                    end_hour, end_minute = map(int, end_time_str.split(':'))
                    end_datetime = datetime.combine(appt_date, time(end_hour, end_minute))
                else:
                    end_datetime = start_datetime + timedelta(minutes=SLOT_DURATION_MINUTES)
                
                busy_slots.append({
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
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
        
        # Add appointments without details from calendar collection
        appointments = get_calendar_appointments(start_date, end_date)
        
        for appt in appointments:
            event = Event()
            event.add('summary', 'Busy')  # Generic title only
            
            # Set date/time - combine date string with time string
            appt_date_str = appt.get('date')  # YYYY-MM-DD
            start_time_str = appt.get('start_time')  # HH:MM
            end_time_str = appt.get('end_time')  # HH:MM
            
            if appt_date_str and start_time_str:
                # Parse date and time
                appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
                start_hour, start_minute = map(int, start_time_str.split(':'))
                start_datetime = datetime.combine(appt_date, time(start_hour, start_minute))
                
                event.add('dtstart', start_datetime)
                
                if end_time_str:
                    end_hour, end_minute = map(int, end_time_str.split(':'))
                    end_datetime = datetime.combine(appt_date, time(end_hour, end_minute))
                    event.add('dtend', end_datetime)
                else:
                    event.add('dtend', start_datetime + timedelta(minutes=SLOT_DURATION_MINUTES))
            
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
