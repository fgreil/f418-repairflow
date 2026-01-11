-- ============================================================================
-- Mobile Phone Repair Shop Database Schema (SQLite)
-- ============================================================================

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS order_services;
DROP TABLE IF EXISTS repair_orders;
DROP TABLE IF EXISTS appointment_slots;
DROP TABLE IF EXISTS repair_services;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS customers;

-- ============================================================================
-- TABLE DEFINITIONS
-- ============================================================================

-- Customers table
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT NOT NULL,
    street_name TEXT NOT NULL,
    house_number TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Devices table
CREATE TABLE devices (
    device_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    imei_number TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand, model, imei_number)
);

-- Repair services catalog
CREATE TABLE repair_services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL UNIQUE,
    base_price DECIMAL(10, 2) NOT NULL,
    estimated_duration_minutes INTEGER DEFAULT 60,
    is_active INTEGER DEFAULT 1
);

-- Appointment slots (for scheduling)
CREATE TABLE appointment_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_date DATE NOT NULL,
    slot_time TIME NOT NULL,
    is_available INTEGER DEFAULT 1,
    max_capacity INTEGER DEFAULT 1,
    current_bookings INTEGER DEFAULT 0,
    UNIQUE(slot_date, slot_time)
);

-- Repair orders
CREATE TABLE repair_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    service_type TEXT CHECK(service_type IN ('walk-in', 'send-in')) NOT NULL,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('pending_quote', 'quoted', 'confirmed', 'in_progress', 'completed', 'cancelled')) DEFAULT 'pending_quote',
    appointment_date DATE,
    appointment_time TIME,
    additional_notes TEXT,
    total_quoted_price DECIMAL(10, 2),
    total_actual_price DECIMAL(10, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Junction table for order services (many-to-many)
CREATE TABLE order_services (
    order_service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    quoted_price DECIMAL(10, 2),
    actual_price DECIMAL(10, 2),
    FOREIGN KEY (order_id) REFERENCES repair_orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES repair_services(service_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_repair_orders_customer ON repair_orders(customer_id);
CREATE INDEX idx_repair_orders_status ON repair_orders(status);
CREATE INDEX idx_repair_orders_appointment ON repair_orders(appointment_date, appointment_time);
CREATE INDEX idx_appointment_slots_date ON appointment_slots(slot_date, is_available);

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Insert sample repair services
INSERT INTO repair_services (service_name, base_price, estimated_duration_minutes) VALUES
    ('Screen Replacement', 89.99, 45),
    ('Battery Replacement', 49.99, 30),
    ('Charging Port Repair', 39.99, 30),
    ('Camera Repair', 79.99, 60),
    ('Water Damage Repair', 99.99, 120),
    ('Speaker Replacement', 44.99, 40),
    ('Back Glass Replacement', 69.99, 45),
    ('Software Troubleshooting', 29.99, 30);

-- Insert sample customers
INSERT INTO customers (first_name, last_name, email, phone_number, street_name, house_number, postal_code, city) VALUES
    ('John', 'Smith', 'john.smith@email.com', '+1-555-0101', 'Main Street', '123', '10001', 'New York'),
    ('Emma', 'Johnson', 'emma.j@email.com', '+1-555-0102', 'Oak Avenue', '456', '10002', 'New York'),
    ('Michael', 'Brown', 'mbrown@email.com', '+1-555-0103', 'Park Road', '789', '10003', 'Brooklyn'),
    ('Sarah', 'Davis', 'sarah.davis@email.com', '+1-555-0104', 'Elm Street', '321', '10004', 'Queens');

-- Insert sample devices
INSERT INTO devices (brand, model, imei_number) VALUES
    ('Apple', 'iPhone 14 Pro', '123456789012345'),
    ('Samsung', 'Galaxy S23', '234567890123456'),
    ('Apple', 'iPhone 13', '345678901234567'),
    ('Google', 'Pixel 8', '456789012345678'),
    ('Samsung', 'Galaxy A54', NULL);

-- Insert appointment slots for next 7 days (9 AM to 5 PM, hourly slots)
INSERT INTO appointment_slots (slot_date, slot_time, is_available, max_capacity, current_bookings) VALUES
    -- Today
    (date('now'), '09:00', 1, 2, 0),
    (date('now'), '10:00', 1, 2, 0),
    (date('now'), '11:00', 1, 2, 1),
    (date('now'), '12:00', 0, 2, 2),
    (date('now'), '13:00', 1, 2, 0),
    (date('now'), '14:00', 1, 2, 0),
    (date('now'), '15:00', 1, 2, 1),
    (date('now'), '16:00', 1, 2, 0),
    (date('now'), '17:00', 1, 2, 0),
    
    -- Tomorrow
    (date('now', '+1 day'), '09:00', 1, 2, 0),
    (date('now', '+1 day'), '10:00', 1, 2, 0),
    (date('now', '+1 day'), '11:00', 1, 2, 0),
    (date('now', '+1 day'), '12:00', 1, 2, 0),
    (date('now', '+1 day'), '13:00', 1, 2, 0),
    (date('now', '+1 day'), '14:00', 1, 2, 0),
    (date('now', '+1 day'), '15:00', 1, 2, 0),
    (date('now', '+1 day'), '16:00', 1, 2, 0),
    (date('now', '+1 day'), '17:00', 1, 2, 0),
    
    -- Day after tomorrow
    (date('now', '+2 days'), '09:00', 1, 2, 0),
    (date('now', '+2 days'), '10:00', 1, 2, 0),
    (date('now', '+2 days'), '11:00', 1, 2, 0),
    (date('now', '+2 days'), '12:00', 1, 2, 0),
    (date('now', '+2 days'), '13:00', 1, 2, 0),
    (date('now', '+2 days'), '14:00', 1, 2, 0),
    (date('now', '+2 days'), '15:00', 1, 2, 0),
    (date('now', '+2 days'), '16:00', 1, 2, 0),
    (date('now', '+2 days'), '17:00', 1, 2, 0);

-- Insert sample repair orders
INSERT INTO repair_orders (customer_id, device_id, service_type, status, appointment_date, appointment_time, additional_notes, total_quoted_price) VALUES
    (1, 1, 'walk-in', 'confirmed', date('now'), '11:00', 'Screen cracked in upper right corner', 89.99),
    (2, 2, 'send-in', 'in_progress', NULL, NULL, 'Battery drains very quickly', 49.99),
    (3, 3, 'walk-in', 'completed', date('now', '-1 day'), '14:00', 'Phone wont charge', 39.99);

-- Insert order services (linking orders to specific repairs)
INSERT INTO order_services (order_id, service_id, quoted_price, actual_price) VALUES
    (1, 1, 89.99, NULL),  -- Screen replacement for order 1
    (2, 2, 49.99, 49.99), -- Battery replacement for order 2
    (3, 3, 39.99, 39.99); -- Charging port for order 3

-- ============================================================================
-- EXAMPLE QUERY 1: GET FREE APPOINTMENT SLOTS
-- ============================================================================

-- Get all available appointment slots for the next 7 days
SELECT 
    slot_date,
    slot_time,
    (max_capacity - current_bookings) as available_spots,
    max_capacity
FROM appointment_slots
WHERE is_available = 1
    AND current_bookings < max_capacity
    AND slot_date >= date('now')
    AND slot_date <= date('now', '+7 days')
ORDER BY slot_date, slot_time;

-- Get available slots for a specific date
-- Example: Replace 'YYYY-MM-DD' with desired date
/*
SELECT 
    slot_date,
    slot_time,
    (max_capacity - current_bookings) as available_spots
FROM appointment_slots
WHERE is_available = 1
    AND current_bookings < max_capacity
    AND slot_date = '2024-01-15'
ORDER BY slot_time;
*/

-- Get next available slot
SELECT 
    slot_date,
    slot_time,
    (max_capacity - current_bookings) as available_spots
FROM appointment_slots
WHERE is_available = 1
    AND current_bookings < max_capacity
    AND (slot_date > date('now') OR (slot_date = date('now') AND slot_time > time('now')))
ORDER BY slot_date, slot_time
LIMIT 1;

-- ============================================================================
-- EXAMPLE QUERY 2: PERSIST DATA FROM REPAIRFLOW.HTM
-- ============================================================================

-- This is a transaction example showing how to insert all data collected 
-- from the repair flow form in the correct order

BEGIN TRANSACTION;

-- Step 1: Insert or get customer
-- First check if customer exists by email
INSERT OR IGNORE INTO customers (
    first_name, 
    last_name, 
    email, 
    phone_number, 
    street_name, 
    house_number, 
    postal_code, 
    city
) VALUES (
    'Jane',              -- from form: First Name
    'Doe',               -- from form: Last Name
    'jane.doe@email.com',-- from form: Email Address
    '+1-555-0199',       -- from form: Phone Number
    'Broadway',          -- from form: Street Name
    '555',               -- from form: House Number
    '10005',             -- from form: Postal Code
    'Manhattan'          -- from form: City
);

-- Get the customer_id (either newly inserted or existing)
-- In application code, you would use: SELECT last_insert_rowid() 
-- or SELECT customer_id FROM customers WHERE email = 'jane.doe@email.com'

-- Step 2: Insert device
INSERT INTO devices (brand, model, imei_number) VALUES (
    'Apple',             -- from form: Selected Brand
    'iPhone 15 Pro',     -- from form: Selected Model
    '789012345678901'    -- from form: IMEI Number (Optional)
);

-- Step 3: Insert repair order
INSERT INTO repair_orders (
    customer_id,
    device_id,
    service_type,
    status,
    appointment_date,
    appointment_time,
    additional_notes,
    total_quoted_price
) VALUES (
    5,                   -- customer_id from step 1 (last_insert_rowid or queried)
    6,                   -- device_id from step 2 (last_insert_rowid)
    'walk-in',           -- from form: selected service type (walk-in or send-in)
    'pending_quote',     -- initial status
    date('now', '+1 day'), -- from form: Selected appointment date
    '10:00',             -- from form: Selected time slot
    'Screen has multiple cracks', -- from form: Additional Notes
    139.98               -- calculated from selected repairs
);

-- Step 4: Insert selected repair services
-- This assumes the customer selected services with IDs 1 and 2
INSERT INTO order_services (order_id, service_id, quoted_price) VALUES
    (4, 1, 89.99),  -- Screen Replacement
    (4, 2, 49.99);  -- Battery Replacement

-- Step 5: Update appointment slot (decrement available spots)
UPDATE appointment_slots
SET current_bookings = current_bookings + 1
WHERE slot_date = date('now', '+1 day')
    AND slot_time = '10:00';

COMMIT;

-- ============================================================================
-- PRACTICAL APPLICATION CODE EXAMPLE (Pseudo-code for reference)
-- ============================================================================

/*
Python/Application pseudo-code for inserting repair flow data:

def save_repair_request(form_data):
    conn = sqlite3.connect('repair_shop.db')
    cursor = conn.cursor()
    
    try:
        # Step 1: Insert customer (or get existing)
        cursor.execute('''
            INSERT OR IGNORE INTO customers 
            (first_name, last_name, email, phone_number, street_name, 
             house_number, postal_code, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (form_data['first_name'], form_data['last_name'], 
              form_data['email'], form_data['phone_number'],
              form_data['street_name'], form_data['house_number'],
              form_data['postal_code'], form_data['city']))
        
        customer_id = cursor.execute(
            'SELECT customer_id FROM customers WHERE email = ?',
            (form_data['email'],)
        ).fetchone()[0]
        
        # Step 2: Insert device
        cursor.execute('''
            INSERT INTO devices (brand, model, imei_number)
            VALUES (?, ?, ?)
        ''', (form_data['brand'], form_data['model'], 
              form_data.get('imei_number')))
        
        device_id = cursor.lastrowid
        
        # Step 3: Calculate total price
        total_price = sum(service['price'] for service in form_data['selected_services'])
        
        # Step 4: Insert repair order
        cursor.execute('''
            INSERT INTO repair_orders 
            (customer_id, device_id, service_type, appointment_date, 
             appointment_time, additional_notes, total_quoted_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, device_id, form_data['service_type'],
              form_data.get('appointment_date'), 
              form_data.get('appointment_time'),
              form_data.get('notes'), total_price))
        
        order_id = cursor.lastrowid
        
        # Step 5: Insert order services
        for service in form_data['selected_services']:
            cursor.execute('''
                INSERT INTO order_services (order_id, service_id, quoted_price)
                VALUES (?, ?, ?)
            ''', (order_id, service['id'], service['price']))
        
        # Step 6: Update appointment slot if booked
        if form_data.get('appointment_date'):
            cursor.execute('''
                UPDATE appointment_slots
                SET current_bookings = current_bookings + 1
                WHERE slot_date = ? AND slot_time = ?
            ''', (form_data['appointment_date'], form_data['appointment_time']))
        
        conn.commit()
        return order_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
*/

-- ============================================================================
-- USEFUL QUERIES FOR MANAGING THE REPAIR SHOP
-- ============================================================================

-- Get all pending orders
SELECT 
    ro.order_id,
    c.first_name || ' ' || c.last_name as customer_name,
    c.email,
    d.brand || ' ' || d.model as device,
    ro.service_type,
    ro.status,
    ro.total_quoted_price
FROM repair_orders ro
JOIN customers c ON ro.customer_id = c.customer_id
JOIN devices d ON ro.device_id = d.device_id
WHERE ro.status IN ('pending_quote', 'quoted', 'confirmed')
ORDER BY ro.order_date;

-- Get today's appointments
SELECT 
    ro.order_id,
    c.first_name || ' ' || c.last_name as customer_name,
    c.phone_number,
    d.brand || ' ' || d.model as device,
    ro.appointment_time,
    GROUP_CONCAT(rs.service_name, ', ') as services
FROM repair_orders ro
JOIN customers c ON ro.customer_id = c.customer_id
JOIN devices d ON ro.device_id = d.device_id
JOIN order_services os ON ro.order_id = os.order_id
JOIN repair_services rs ON os.service_id = rs.service_id
WHERE ro.appointment_date = date('now')
GROUP BY ro.order_id
ORDER BY ro.appointment_time;

-- Get order details with all repairs
SELECT 
    ro.order_id,
    c.first_name || ' ' || c.last_name as customer_name,
    c.email,
    c.phone_number,
    d.brand,
    d.model,
    d.imei_number,
    ro.service_type,
    ro.status,
    ro.order_date,
    ro.appointment_date,
    ro.appointment_time,
    ro.additional_notes,
    GROUP_CONCAT(rs.service_name || ' ($' || os.quoted_price || ')', '; ') as services,
    ro.total_quoted_price
FROM repair_orders ro
JOIN customers c ON ro.customer_id = c.customer_id
JOIN devices d ON ro.device_id = d.device_id
JOIN order_services os ON ro.order_id = os.order_id
JOIN repair_services rs ON os.service_id = rs.service_id
WHERE ro.order_id = 1  -- Replace with specific order_id
GROUP BY ro.order_id;
