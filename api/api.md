# RepairFlow REST API 

This API enables customers to request device repair quotes and book appointments, and offers the repair shop the possibility to manage requests, quotes, and the schedule.

**Base URL:** `tbd/v1`

## Customer Endpoints

### Get Available Appointments

Retrieve available time slots for a specific date or date range.

```
GET /appointments/available
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (ISO 8601) | No | Specific date (default: today) |
| `start_date` | string (ISO 8601) | No | Start of date range |
| `end_date` | string (ISO 8601) | No | End of date range |
| `service_type` | string | No | Filter by service type (`shop_visit`, `send_device`) |

**Response (200 OK):**

```json
{
  "available_slots": [
    {
      "date": "2026-01-15",
      "time": "09:00",
      "slot_id": "slot_abc123",
      "service_type": "shop_visit"
    },
    {
      "date": "2026-01-15",
      "time": "10:00",
      "slot_id": "slot_def456",
      "service_type": "shop_visit"
    }
  ]
}
```

### Submit Repair Request

Submit a complete repair request with customer details and selected appointment.

```
POST /repair-requests
```

**Request Body:**

```json
{
  "device": {
    "brand": "Apple",
    "model": "iPhone 14 Pro",
    "imei": "123456789012345"
  },
  "repairs": [
    "Screen Replacement",
    "Battery Replacement"
  ],
  "service_type": "shop_visit",
  "customer": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+49123456789",
    "address": {
      "street": "Main Street",
      "house_number": "42",
      "postal_code": "12345",
      "city": "Berlin"
    }
  },
  "appointment": {
    "slot_id": "slot_abc123",
    "date": "2026-01-15",
    "time": "09:00"
  },
  "notes": "Screen is completely shattered"
}
```

**Response (201 Created):**

```json
{
  "request_id": "req_xyz789",
  "status": "pending_quote",
  "confirmation_number": "RFW-2026-0001",
  "message": "We'll contact you shortly with a detailed quote",
  "estimated_response_time": "24 hours"
}
```


### Get Repair Request Status

Retrieve the status and details of a repair request.

```
GET /repair-requests/{request_id}
```

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "confirmation_number": "RFW-2026-0001",
  "status": "quote_sent",
  "submitted_at": "2026-01-12T10:30:00Z",
  "device": {
    "brand": "Apple",
    "model": "iPhone 14 Pro"
  },
  "repairs": ["Screen Replacement", "Battery Replacement"],
  "quote": {
    "amount": 299.99,
    "currency": "EUR",
    "sent_at": "2026-01-12T14:00:00Z",
    "valid_until": "2026-01-19T14:00:00Z"
  },
  "appointment": {
    "date": "2026-01-15",
    "time": "09:00",
    "service_type": "shop_visit"
  }
}
```

### Cancel Repair Request

Cancel an existing repair request and free up the appointment slot.

```
DELETE /repair-requests/{request_id}
```

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "status": "cancelled",
  "message": "Repair request cancelled successfully"
}
```

## Endpoints for the Repair shop

All admin endpoints require authentication via Bearer token.

**Authorization Header:** `Authorization: Bearer {token}`

### Get All Repair Requests

Retrieve a list of all repair requests with filtering options.

```
GET /admin/repair-requests
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status (`pending_quote`, `quote_sent`, `confirmed`, `in_progress`, `completed`, `cancelled`) |
| `start_date` | string (ISO 8601) | No | Filter requests from this date |
| `end_date` | string (ISO 8601) | No | Filter requests until this date |
| `page` | integer | No | Page number (default: 1) |
| `limit` | integer | No | Results per page (default: 50) |

**Response (200 OK):**

```json
{
  "requests": [
    {
      "request_id": "req_xyz789",
      "confirmation_number": "RFW-2026-0001",
      "status": "quote_sent",
      "customer": {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+49123456789"
      },
      "device": {
        "brand": "Apple",
        "model": "iPhone 14 Pro"
      },
      "repairs": ["Screen Replacement", "Battery Replacement"],
      "appointment": {
        "date": "2026-01-15",
        "time": "09:00"
      },
      "quote_amount": 299.99,
      "submitted_at": "2026-01-12T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1,
    "total_pages": 1
  }
}
```

### Get Single Repair Request (Admin)

Get detailed information about a specific repair request.

```
GET /admin/repair-requests/{request_id}
```

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "confirmation_number": "RFW-2026-0001",
  "status": "quote_sent",
  "submitted_at": "2026-01-12T10:30:00Z",
  "device": {
    "brand": "Apple",
    "model": "iPhone 14 Pro",
    "imei": "123456789012345"
  },
  "repairs": ["Screen Replacement", "Battery Replacement"],
  "customer": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+49123456789",
    "address": {
      "street": "Main Street",
      "house_number": "42",
      "postal_code": "12345",
      "city": "Berlin"
    }
  },
  "service_type": "shop_visit",
  "appointment": {
    "date": "2026-01-15",
    "time": "09:00",
    "slot_id": "slot_abc123"
  },
  "quote": {
    "amount": 299.99,
    "currency": "EUR",
    "sent_at": "2026-01-12T14:00:00Z",
    "valid_until": "2026-01-19T14:00:00Z"
  },
  "notes": "Screen is completely shattered",
  "history": [
    {
      "timestamp": "2026-01-12T10:30:00Z",
      "action": "request_submitted"
    },
    {
      "timestamp": "2026-01-12T14:00:00Z",
      "action": "quote_sent",
      "details": "Quote sent via email"
    }
  ]
}
```

---

### Send Quote

Send a price quote to a customer for their repair request.

```
POST /admin/repair-requests/{request_id}/quote
```

**Request Body:**

```json
{
  "amount": 299.99,
  "currency": "EUR",
  "valid_for_days": 7,
  "notes": "Parts available, can complete within 2 hours"
}
```

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "quote": {
    "amount": 299.99,
    "currency": "EUR",
    "sent_at": "2026-01-12T14:00:00Z",
    "valid_until": "2026-01-19T14:00:00Z"
  },
  "status": "quote_sent",
  "message": "Quote sent successfully to customer"
}
```

### Update Repair Request Status

Update the status of a repair request.

```
PATCH /admin/repair-requests/{request_id}/status
```

**Request Body:**

```json
{
  "status": "in_progress",
  "notes": "Customer confirmed, repair started"
}
```

**Allowed Status Values:**
- `pending_quote`
- `quote_sent`
- `confirmed`
- `in_progress`
- `completed`
- `cancelled`

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "status": "in_progress",
  "updated_at": "2026-01-15T09:15:00Z"
}
```

### Reschedule Appointment (Admin)

Reschedule a customer's appointment from the admin side.

```
PATCH /admin/repair-requests/{request_id}/appointment
```

**Request Body:**

```json
{
  "slot_id": "slot_new456",
  "date": "2026-01-16",
  "time": "14:00",
  "reason": "Technician unavailable",
  "notify_customer": true
}
```

**Response (200 OK):**

```json
{
  "request_id": "req_xyz789",
  "appointment": {
    "date": "2026-01-16",
    "time": "14:00"
  },
  "message": "Appointment rescheduled, customer notified via email"
}
```

---

### Get Calendar (All Appointments)

Retrieve all scheduled appointments with their details.

```
GET /admin/calendar
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string (ISO 8601) | No | Start date (default: today) |
| `end_date` | string (ISO 8601) | No | End date (default: 30 days from start) |
| `status` | string | No | Filter by request status |
| `service_type` | string | No | Filter by service type |

**Response (200 OK):**

```json
{
  "appointments": [
    {
      "appointment_id": "appt_001",
      "date": "2026-01-15",
      "time": "09:00",
      "slot_id": "slot_abc123",
      "duration_minutes": 120,
      "service_type": "shop_visit",
      "request": {
        "request_id": "req_xyz789",
        "confirmation_number": "RFW-2026-0001",
        "status": "confirmed",
        "customer_name": "John Doe",
        "customer_phone": "+49123456789",
        "device": "Apple iPhone 14 Pro",
        "repairs": ["Screen Replacement", "Battery Replacement"]
      }
    },
    {
      "appointment_id": "appt_002",
      "date": "2026-01-15",
      "time": "11:00",
      "slot_id": "slot_def456",
      "duration_minutes": 60,
      "service_type": "shop_visit",
      "request": {
        "request_id": "req_abc456",
        "confirmation_number": "RFW-2026-0002",
        "status": "confirmed",
        "customer_name": "Jane Smith",
        "customer_phone": "+49987654321",
        "device": "Samsung Galaxy S23",
        "repairs": ["Battery Replacement"]
      }
    }
  ],
  "date_range": {
    "start": "2026-01-15",
    "end": "2026-02-14"
  },
  "total_appointments": 2
}
```

---

### Manage Appointment Slots

Create or update available appointment slots.

```
POST /admin/calendar/slots
```

**Request Body:**

```json
{
  "date": "2026-01-20",
  "slots": [
    {
      "time": "09:00",
      "duration_minutes": 120,
      "service_types": ["shop_visit", "send_device"],
      "available": true
    },
    {
      "time": "11:00",
      "duration_minutes": 120,
      "service_types": ["shop_visit"],
      "available": true
    }
  ]
}
```

**Response (201 Created):**

```json
{
  "date": "2026-01-20",
  "slots_created": 2,
  "message": "Appointment slots created successfully"
}
```

---

## Data Models

### Status Values

| Status | Description |
|--------|-------------|
| `pending_quote` | Request received, awaiting quote from shop |
| `quote_sent` | Quote sent to customer |
| `confirmed` | Customer confirmed appointment |
| `in_progress` | Repair work in progress |
| `completed` | Repair completed |
| `cancelled` | Request cancelled by customer or shop |

### Service Types

| Type | Description |
|------|-------------|
| `shop_visit` | Customer visits shop for repair |
| `send_device` | Customer sends device for repair |

---

## Error Responses

All endpoints may return the following error responses:

**400 Bad Request:**
```json
{
  "error": "invalid_request",
  "message": "Missing required field: customer.email"
}
```

**401 Unauthorized (Admin endpoints):**
```json
{
  "error": "unauthorized",
  "message": "Invalid or missing authentication token"
}
```

**404 Not Found:**
```json
{
  "error": "not_found",
  "message": "Repair request not found"
}
```

**409 Conflict:**
```json
{
  "error": "slot_unavailable",
  "message": "Selected appointment slot is no longer available"
}
```

**500 Internal Server Error:**
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred"
}
```

---

## Rate Limiting

- **Customer endpoints:** 60 requests per minute per IP
- **Admin endpoints:** 300 requests per minute per token

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Optional webhooks

Configure webhooks to receive notifications for events:

**Events:**
- `request.created` - New repair request submitted
- `request.cancelled` - Request cancelled
- `appointment.rescheduled` - Appointment time changed
- `quote.sent` - Quote sent to customer
- `status.updated` - Request status changed

**Webhook Payload Example:**
```json
{
  "event": "request.created",
  "timestamp": "2026-01-12T10:30:00Z",
  "data": {
    "request_id": "req_xyz789",
    "confirmation_number": "RFW-2026-0001"
  }
}
```
