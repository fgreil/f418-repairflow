We are aiming for simple appointment booking system:

In `app.py` we use global variables to define
* the size of the slots (for example 30 minutes)
* available work days (currently Monday to Saturday)
* working hours for each day (for now: Monday-Friday 9:00-16:00, Saturday 10-15:00)
* recurring closing days per year (May 1st, October 3rd, December 25th and 26th for now)

The **endpoint `/slots`** shows the available slots in the future up to a certain day, e.g. `this_week`, `next_week`, `this_month`, `next_month, `this_year`

The **endpoint `/slot`** allows (the administrator &mdash; access control comes immediately after core architecture is done) for method `GET` shows details on an appointment.
For method `POST`, the admin can chancel or update an appointment. 

The **endpoint `/appointments`** shows the same info as `/slots` additional details (for the admin): It answers who booked which slot with reference to the request-collection, 
but also duplicates name, email, phone of the customer as well as as details on the device (brand, model, color, IMEI).

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











