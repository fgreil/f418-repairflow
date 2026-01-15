# Backend for `f418-repairflow`

We are aiming for simple appointment booking system.

In `app.py` we use global variables to define
* the size of the slots (for example 30 minutes)
* available work days (currently Monday to Saturday)
* working hours for each day (for now: Monday-Friday 9:00-16:00, Saturday 10-15:00)
* recurring closing days per year (May 1st, October 3rd, December 25th and 26th for now)

## Endpoints

* `GET /` &mdash; **API Documentation.**  JSON with all available endpoints and their descriptions
* `GET /sorry` &mdash; **Random BOFH Excuse.** Random excuse from fortune command
* `GET /options` &mdash; **Get Available Filter Options**
   - Parameters:
     - `filter` (required) - Type of options: `device_types`, `brands`, `models`, `postal_codes`, `cities`
     - `device_type` (optional) - For `models` filter: limit to specific device type
     - `brand` (optional) - For `models` filter: limit to specific brand
   - Returns: JSON with sorted list of available options (max 50 entries)
   - Examples: `/options?filter=device_types`, `/options?filter=models&device_type=smartphone`, `/options?filter=models&brand=Samsung`
* `GET /requests` &mdash; **List and Search Repair Requests**
   - Parameters (all optional, can be combined):
     - `start_date` (YYYY-MM-DD) - Start of date range (default: today)
     - `end_date` (YYYY-MM-DD) - End of date range (default: start_date + 90 days)
     - `device_type` - Filter by device type
     - `brand` - Filter by manufacturer/brand
     - `model` - Filter by device model
     - `postal_code` - Filter by customer postal code
     - `customer_search` - Search across all customer fields (name, email, phone, address)
     - `limit` (integer) - Maximum results (default: 10, max: 50)
   - Returns: JSON with matching repair requests, search metadata (count, total_found, search_time_ms)
   - Examples: `/requests?device_type=smartphone&limit=20`, `/requests?customer_search=John&start_date=2025-01-01`, `/requests?brand=Samsung&postal_code=12345`
* `GET /request?id=<id>` &mdash; **Get Specific Repair Request**
   - Parameters: `id` (required) - MongoDB ObjectId
   - Returns: Complete repair request document
* `POST /request` &mdash; **Create New Repair Request**
   - Required fields: `customer`, `device`, `serviceType`
   - Optional fields: `repairs`, `appointment`, `status`, `totalQuotedPrice`, `totalActualPrice`, `additionalNotes`
   - Returns: ID of newly created request
* `GET /calendar` 🔒 **Full Calendar with Details (Protected, JSON)**
  - Authentication: HTTP Basic Auth required
  - Returns: JSON with complete appointment information for next 90 days
  - Includes: Customer names, contact info, device details, request IDs 
* `GET /calendar.ics` 🔒 **Full Calendar with Details (Protected).**
  - Authentication: HTTP Basic Auth required
  - Returns: iCalendar file with complete appointment information
  - Includes: Customer names, contact info, device details, service type, notes
  - Use: Subscribe in Thunderbird/Outlook for full access
* `GET /slots?range=<range>` &mdash; **Available Slots (Public, JSON)**
  - Parameters: `range` (optional) - `today` (default), `this_week` (current week until Sunday), `next_week`, `this_month`, `next_month`, `this_year`
  - Returns: JSON with busy/free slots, no customer details
  - Shows: Time slots marked as "booked" or "closed"
* `GET /slots.ics` &mdash; **Available Slots (Public, iCalendar)**
  - Returns: iCalendar file showing busy/free times without details
  - Shows: Generic "Busy" entries for appointments, "Unavailable" for non-working hours
  - Use: Subscribe in calendar apps for availability view

## MongoDB side 
Updating `app.py` is enough, MongoDB will handle the rest automatically. Two optional optimizations can be added later:
* Indices for better query performance
  ```
  db.appointments.createIndex({ "datetime": 1, "status": 1 })
  db.appointments.createIndex({ "requestId": 1 })
  db.repair_requests.createIndex({ "customer.email": 1 })
  db.repair_requests.createIndex({ "submittedAt": -1 })
  ```
* If you want MongoDB to enforce schema constraints you can enforce it with the following **validation rules**:
  ```
  db.createCollection("appointments", {
     validator: {
        $jsonSchema: {
           required: ["datetime", "status", "customer", "device"],
           properties: {
              datetime: { bsonType: "date" },
              status: { enum: ["booked", "confirmed", "completed", "cancelled", "no_show"] }
           }
        }
     }
  })
  ```











