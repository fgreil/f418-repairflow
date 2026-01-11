# Mobile Phone Repair Shop Database

Database schemas for managing mobile phone repair workflows, supporting both SQLite (relational) and MongoDB (document-based) approaches.
Base for the schemata is the [web form](repairflow.htm) where (potential) customers select their device, choose repairs, and optionally book appointments.

## SQLite (Relational)

**Best for:** Traditional applications, strong data consistency, complex reporting

**Structure:**
- Normalized tables with foreign key relationships
- Separate tables: `customers`, `devices`, `repair_services`, `repair_orders`, `order_services`, `appointment_slots`
- Junction table for many-to-many order-service relationships

**Advantages:**
- Strong data integrity with constraints
- Efficient for complex joins and aggregations
- Reduced data duplication
- ACID compliance built-in

**Setup:**
```bash
sqlite3 repair_shop.db < repair_shop.sql
```

### MongoDB (Document-Based)

**Best for:** Flexible schemas, horizontal scaling, self-contained documents

**Structure:**
- One document per repair submission in `repair_requests` collection
- Embedded customer, device, and repairs data
- Separate collections: `appointment_slots`, `repair_services` (reference data)

**Advantages:**
- Single document contains complete repair history
- No joins needed for most queries
- Historical snapshot of customer data preserved
- Easy schema evolution

**Setup:**
```bash
mongosh repair_shop < repair_shop_mongodb.js
```

## Core Features

Both implementations support:

1. **Customer Management** - Store contact and address information
2. **Device Tracking** - Brand, model, and IMEI registration
3. **Service Catalog** - Repair types with pricing
4. **Order Management** - Track repair requests through workflow stages
5. **Appointment Scheduling** - Time slot booking with capacity limits
6. **Multiple Repairs** - Single order can include multiple services

## Key Queries

### 1. Get Free Appointment Slots

**SQLite:**
```sql
SELECT slot_date, slot_time, 
       (max_capacity - current_bookings) as available_spots
FROM appointment_slots
WHERE is_available = 1 
  AND current_bookings < max_capacity
  AND slot_date >= date('now')
ORDER BY slot_date, slot_time;
```

**MongoDB:**
```javascript
db.appointment_slots.find(
  {
    isAvailable: true,
    currentBookings: { $lt: "$maxCapacity" },
    date: { $gte: new Date() }
  }
).sort({ date: 1, time: 1 });
```

### 2. Persist Repair Flow Submission

**SQLite:** (Transaction required)
```sql
BEGIN TRANSACTION;

-- Insert customer
INSERT INTO customers (...) VALUES (...);

-- Insert device
INSERT INTO devices (...) VALUES (...);

-- Insert repair order
INSERT INTO repair_orders (...) VALUES (...);

-- Insert selected services
INSERT INTO order_services (...) VALUES (...);

-- Update appointment slot
UPDATE appointment_slots 
SET current_bookings = current_bookings + 1
WHERE slot_date = ? AND slot_time = ?;

COMMIT;
```

**MongoDB:** (Single operation)
```javascript
db.repair_requests.insertOne({
  customer: { firstName, lastName, email, ... },
  device: { brand, model, imeiNumber },
  repairs: [
    { serviceName, quotedPrice, estimatedDuration }
  ],
  serviceType: "walk-in",
  appointment: { date, time },
  status: "pending_quote",
  totalQuotedPrice: NumberDecimal("139.98"),
  submittedAt: new Date()
});

// Update slot availability
db.appointment_slots.updateOne(
  { date: appointmentDate, time: appointmentTime },
  { 
    $inc: { currentBookings: 1 },
    $push: { bookedBy: { requestId, customerEmail } }
  }
);
```

## Workflow States

Both systems track repairs through these stages:

1. **pending_quote** - Initial submission, awaiting price confirmation
2. **quoted** - Price provided to customer
3. **confirmed** - Customer accepted quote
4. **in_progress** - Repair work started
5. **completed** - Repair finished
6. **cancelled** - Request cancelled

## Service Types

- **walk-in** - Customer visits shop, repair while they wait
- **send-in** - Customer ships device, 24-hour turnaround

## Data Model Comparison

| Aspect | SQLite | MongoDB |
|--------|--------|---------|
| Customer data | Normalized, single record | Embedded in each request |
| Relationships | Foreign keys | Embedded documents + refs |
| Data duplication | Minimal | Intentional (historical) |
| Query complexity | Joins required | Single document lookup |
| Schema changes | Migration required | Flexible, backward compatible |
| Transactions | Built-in | Requires replica set |

## Common Queries

### Get Today's Appointments

**SQLite:**
```sql
SELECT c.first_name, c.last_name, d.brand, d.model, 
       ro.appointment_time
FROM repair_orders ro
JOIN customers c ON ro.customer_id = c.customer_id
JOIN devices d ON ro.device_id = d.device_id
WHERE ro.appointment_date = date('now')
ORDER BY ro.appointment_time;
```

**MongoDB:**
```javascript
db.repair_requests.find({
  "appointment.date": {
    $gte: new Date(new Date().setHours(0,0,0,0)),
    $lte: new Date(new Date().setHours(23,59,59,999))
  }
}).sort({ "appointment.time": 1 });
```

### Customer Repair History

**SQLite:**
```sql
SELECT ro.order_date, d.brand, d.model, 
       GROUP_CONCAT(rs.service_name) as repairs
FROM repair_orders ro
JOIN customers c ON ro.customer_id = c.customer_id
JOIN devices d ON ro.device_id = d.device_id
JOIN order_services os ON ro.order_id = os.order_id
JOIN repair_services rs ON os.service_id = rs.service_id
WHERE c.email = 'customer@email.com'
GROUP BY ro.order_id
ORDER BY ro.order_date DESC;
```

**MongoDB:**
```javascript
db.repair_requests.find({
  "customer.email": "customer@email.com"
}).sort({ submittedAt: -1 });
```

## Files Included

- `repair_shop.sql` - SQLite schema, sample data, and queries
- `repair_shop_mongodb.js` - MongoDB collections, validators, and operations
- `README.md` - This documentation

## Choosing an Approach

**Choose SQLite if:**
- You need strong referential integrity
- Complex reporting and analytics are primary use case
- Data consistency is critical
- Single-server deployment

**Choose MongoDB if:**
- You need flexible, evolving schemas
- Horizontal scaling is anticipated
- Document-oriented workflow fits naturally
- Historical snapshots are valuable
- Faster development iteration preferred
