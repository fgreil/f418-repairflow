// ============================================================================
// Mobile Phone Repair Shop - MongoDB Schema and Operations
// ============================================================================
// Approach: Each repair flow submission creates one main document
// ============================================================================

// ============================================================================
// Database Setup
// ============================================================================

// Switch to (and create if not exists) the repair shop database
use repair_shop;
print("Using database: " + db.getName());
print("Starting setup...\n");

// ============================================================================
// COLLECTION STRUCTURES
// ============================================================================

// ---------------------------------------------------------------------------
// Collection: repair_requests
// Main collection - one document per repair flow submission
// ---------------------------------------------------------------------------
db.createCollection("repair_requests", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["customer", "device", "serviceType", "submittedAt"],
      properties: {
        customer: {
          bsonType: "object",
          required: ["firstName", "lastName", "email", "phoneNumber", "address"],
          properties: {
            firstName: { bsonType: "string" },
            lastName: { bsonType: "string" },
            email: { bsonType: "string" },
            phoneNumber: { bsonType: "string" },
            address: {
              bsonType: "object",
              required: ["streetName", "houseNumber", "postalCode", "city"],
              properties: {
                streetName: { bsonType: "string" },
                houseNumber: { bsonType: "string" },
                postalCode: { bsonType: "string" },
                city: { bsonType: "string" }
              }
            }
          }
        },
        device: {
          bsonType: "object",
          required: ["brand", "model"],
          properties: {
            brand: { bsonType: "string" },
            model: { bsonType: "string" },
            imeiNumber: { bsonType: ["string", "null"] }
          }
        },
        repairs: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["serviceName", "quotedPrice"],
            properties: {
              serviceName: { bsonType: "string" },
              quotedPrice: { bsonType: "decimal" },
              actualPrice: { bsonType: ["decimal", "null"] },
              estimatedDuration: { bsonType: "int" }
            }
          }
        },
        serviceType: {
          enum: ["walk-in", "send-in"]
        },
        appointment: {
          bsonType: ["object", "null"],
          properties: {
            date: { bsonType: "date" },
            time: { bsonType: "string" },
            confirmedAt: { bsonType: ["date", "null"] }
          }
        },
        status: {
          enum: ["pending_quote", "quoted", "confirmed", "in_progress", "completed", "cancelled"]
        },
        totalQuotedPrice: { bsonType: "decimal" },
        totalActualPrice: { bsonType: ["decimal", "null"] },
        additionalNotes: { bsonType: ["string", "null"] },
        submittedAt: { bsonType: "date" },
        updatedAt: { bsonType: "date" }
      }
    }
  }
});

// ---------------------------------------------------------------------------
// Collection: appointment_slots
// Manages available time slots for scheduling
// ---------------------------------------------------------------------------
db.createCollection("appointment_slots", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["date", "time", "maxCapacity"],
      properties: {
        date: { bsonType: "date" },
        time: { bsonType: "string" },
        maxCapacity: { bsonType: "int" },
        currentBookings: { bsonType: "int" },
        isAvailable: { bsonType: "bool" },
        bookedBy: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              requestId: { bsonType: "objectId" },
              customerEmail: { bsonType: "string" },
              bookedAt: { bsonType: "date" }
            }
          }
        }
      }
    }
  }
});

// ---------------------------------------------------------------------------
// Collection: repair_services (Reference/Catalog)
// Catalog of available repair services
// ---------------------------------------------------------------------------
db.createCollection("repair_services", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["serviceName", "basePrice"],
      properties: {
        serviceName: { bsonType: "string" },
        basePrice: { bsonType: "decimal" },
        estimatedDuration: { bsonType: "int" },
        isActive: { bsonType: "bool" },
        category: { bsonType: "string" }
      }
    }
  }
});

// ============================================================================
// CREATE INDEXES
// ============================================================================

// Indexes for repair_requests
db.repair_requests.createIndex({ "customer.email": 1 });
db.repair_requests.createIndex({ "submittedAt": -1 });
db.repair_requests.createIndex({ "status": 1 });
db.repair_requests.createIndex({ "appointment.date": 1, "appointment.time": 1 });
db.repair_requests.createIndex({ "device.brand": 1, "device.model": 1 });
db.repair_requests.createIndex({ "customer.phoneNumber": 1 });

// Indexes for appointment_slots
db.appointment_slots.createIndex({ "date": 1, "time": 1 }, { unique: true });
db.appointment_slots.createIndex({ "date": 1, "isAvailable": 1 });

// Indexes for repair_services
db.repair_services.createIndex({ "serviceName": 1 }, { unique: true });
db.repair_services.createIndex({ "isActive": 1 });

// ============================================================================
// SAMPLE DATA
// ============================================================================

// Insert repair services catalog
db.repair_services.insertMany([
  {
    serviceName: "Screen Replacement",
    basePrice: NumberDecimal("89.99"),
    estimatedDuration: 45,
    isActive: true,
    category: "Display"
  },
  {
    serviceName: "Battery Replacement",
    basePrice: NumberDecimal("49.99"),
    estimatedDuration: 30,
    isActive: true,
    category: "Power"
  },
  {
    serviceName: "Charging Port Repair",
    basePrice: NumberDecimal("39.99"),
    estimatedDuration: 30,
    isActive: true,
    category: "Power"
  },
  {
    serviceName: "Camera Repair",
    basePrice: NumberDecimal("79.99"),
    estimatedDuration: 60,
    isActive: true,
    category: "Camera"
  },
  {
    serviceName: "Water Damage Repair",
    basePrice: NumberDecimal("99.99"),
    estimatedDuration: 120,
    isActive: true,
    category: "General"
  },
  {
    serviceName: "Speaker Replacement",
    basePrice: NumberDecimal("44.99"),
    estimatedDuration: 40,
    isActive: true,
    category: "Audio"
  },
  {
    serviceName: "Back Glass Replacement",
    basePrice: NumberDecimal("69.99"),
    estimatedDuration: 45,
    isActive: true,
    category: "Display"
  },
  {
    serviceName: "Software Troubleshooting",
    basePrice: NumberDecimal("29.99"),
    estimatedDuration: 30,
    isActive: true,
    category: "Software"
  }
]);

// Insert appointment slots for the next 7 days (9 AM - 5 PM, hourly)
const today = new Date();
today.setHours(0, 0, 0, 0);

const slots = [];
const timeSlots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"];

for (let day = 0; day < 7; day++) {
  const slotDate = new Date(today);
  slotDate.setDate(today.getDate() + day);
  
  for (let time of timeSlots) {
    slots.push({
      date: slotDate,
      time: time,
      maxCapacity: 2,
      currentBookings: 0,
      isAvailable: true,
      bookedBy: []
    });
  }
}

db.appointment_slots.insertMany(slots);

// Insert sample repair requests
db.repair_requests.insertMany([
  {
    customer: {
      firstName: "John",
      lastName: "Smith",
      email: "john.smith@email.com",
      phoneNumber: "+1-555-0101",
      address: {
        streetName: "Main Street",
        houseNumber: "123",
        postalCode: "10001",
        city: "New York"
      }
    },
    device: {
      brand: "Apple",
      model: "iPhone 14 Pro",
      imeiNumber: "123456789012345"
    },
    repairs: [
      {
        serviceName: "Screen Replacement",
        quotedPrice: NumberDecimal("89.99"),
        actualPrice: null,
        estimatedDuration: 45
      }
    ],
    serviceType: "walk-in",
    appointment: {
      date: new Date(today.getTime() + 24 * 60 * 60 * 1000), // Tomorrow
      time: "10:00",
      confirmedAt: new Date()
    },
    status: "confirmed",
    totalQuotedPrice: NumberDecimal("89.99"),
    totalActualPrice: null,
    additionalNotes: "Screen cracked in upper right corner",
    submittedAt: new Date(),
    updatedAt: new Date()
  },
  {
    customer: {
      firstName: "Emma",
      lastName: "Johnson",
      email: "emma.j@email.com",
      phoneNumber: "+1-555-0102",
      address: {
        streetName: "Oak Avenue",
        houseNumber: "456",
        postalCode: "10002",
        city: "New York"
      }
    },
    device: {
      brand: "Samsung",
      model: "Galaxy S23",
      imeiNumber: "234567890123456"
    },
    repairs: [
      {
        serviceName: "Battery Replacement",
        quotedPrice: NumberDecimal("49.99"),
        actualPrice: NumberDecimal("49.99"),
        estimatedDuration: 30
      }
    ],
    serviceType: "send-in",
    appointment: null,
    status: "in_progress",
    totalQuotedPrice: NumberDecimal("49.99"),
    totalActualPrice: NumberDecimal("49.99"),
    additionalNotes: "Battery drains very quickly",
    submittedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
    updatedAt: new Date()
  },
  {
    customer: {
      firstName: "Michael",
      lastName: "Brown",
      email: "mbrown@email.com",
      phoneNumber: "+1-555-0103",
      address: {
        streetName: "Park Road",
        houseNumber: "789",
        postalCode: "10003",
        city: "Brooklyn"
      }
    },
    device: {
      brand: "Apple",
      model: "iPhone 13",
      imeiNumber: "345678901234567"
    },
    repairs: [
      {
        serviceName: "Charging Port Repair",
        quotedPrice: NumberDecimal("39.99"),
        actualPrice: NumberDecimal("39.99"),
        estimatedDuration: 30
      },
      {
        serviceName: "Battery Replacement",
        quotedPrice: NumberDecimal("49.99"),
        actualPrice: NumberDecimal("49.99"),
        estimatedDuration: 30
      }
    ],
    serviceType: "walk-in",
    appointment: {
      date: new Date(Date.now() - 24 * 60 * 60 * 1000), // Yesterday
      time: "14:00",
      confirmedAt: new Date(Date.now() - 24 * 60 * 60 * 1000)
    },
    status: "completed",
    totalQuotedPrice: NumberDecimal("89.98"),
    totalActualPrice: NumberDecimal("89.98"),
    additionalNotes: "Phone won't charge and battery dies quickly",
    submittedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
    updatedAt: new Date()
  }
]);

// ============================================================================
// QUERY 1: GET FREE APPOINTMENT SLOTS
// ============================================================================

print("\n========================================");
print("QUERY 1: Get Free Appointment Slots");
print("========================================\n");

// Get all available slots for the next 7 days
print("--- All available slots for next 7 days ---");
db.appointment_slots.find(
  {
    isAvailable: true,
    currentBookings: { $lt: 2 }, // Less than max capacity
    date: { 
      $gte: new Date(),
      $lte: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
    }
  },
  {
    date: 1,
    time: 1,
    availableSpots: { $subtract: ["$maxCapacity", "$currentBookings"] },
    maxCapacity: 1,
    _id: 0
  }
).sort({ date: 1, time: 1 }).pretty();

// Get available slots for a specific date
print("\n--- Available slots for a specific date ---");
const specificDate = new Date(today);
specificDate.setDate(today.getDate() + 1); // Tomorrow

db.appointment_slots.aggregate([
  {
    $match: {
      isAvailable: true,
      currentBookings: { $lt: "$maxCapacity" },
      date: {
        $gte: specificDate,
        $lt: new Date(specificDate.getTime() + 24 * 60 * 60 * 1000)
      }
    }
  },
  {
    $project: {
      _id: 0,
      date: 1,
      time: 1,
      availableSpots: { $subtract: ["$maxCapacity", "$currentBookings"] },
      maxCapacity: 1
    }
  },
  {
    $sort: { time: 1 }
  }
]).pretty();

// Get next available slot
print("\n--- Next available slot ---");
db.appointment_slots.findOne(
  {
    isAvailable: true,
    currentBookings: { $lt: 2 },
    date: { $gte: new Date() }
  },
  {
    date: 1,
    time: 1,
    availableSpots: { $subtract: ["$maxCapacity", "$currentBookings"] },
    _id: 0
  }
);

// ============================================================================
// QUERY 2: PERSIST DATA FROM REPAIRFLOW.HTM
// ============================================================================

print("\n========================================");
print("QUERY 2: Persist Repair Flow Submission");
print("========================================\n");

// Example: Complete workflow to save a repair flow submission
// This demonstrates the MongoDB equivalent of the SQL transaction

// Step 1: Prepare the form data (this would come from the web form)
const formData = {
  firstName: "Jane",
  lastName: "Doe",
  email: "jane.doe@email.com",
  phoneNumber: "+1-555-0199",
  streetName: "Broadway",
  houseNumber: "555",
  postalCode: "10005",
  city: "Manhattan",
  brand: "Apple",
  model: "iPhone 15 Pro",
  imeiNumber: "789012345678901",
  serviceType: "walk-in",
  selectedServices: ["Screen Replacement", "Battery Replacement"],
  appointmentDate: new Date(Date.now() + 24 * 60 * 60 * 1000), // Tomorrow
  appointmentTime: "11:00",
  additionalNotes: "Screen has multiple cracks and battery life is poor"
};

// Step 2: Lookup service prices
const serviceDetails = db.repair_services.find(
  { serviceName: { $in: formData.selectedServices } }
).toArray();

// Step 3: Calculate total price and prepare repairs array
let totalPrice = NumberDecimal("0");
const repairs = serviceDetails.map(service => {
  totalPrice = totalPrice.add(service.basePrice);
  return {
    serviceName: service.serviceName,
    quotedPrice: service.basePrice,
    actualPrice: null,
    estimatedDuration: service.estimatedDuration
  };
});

// Step 4: Create the repair request document
const repairRequest = {
  customer: {
    firstName: formData.firstName,
    lastName: formData.lastName,
    email: formData.email,
    phoneNumber: formData.phoneNumber,
    address: {
      streetName: formData.streetName,
      houseNumber: formData.houseNumber,
      postalCode: formData.postalCode,
      city: formData.city
    }
  },
  device: {
    brand: formData.brand,
    model: formData.model,
    imeiNumber: formData.imeiNumber
  },
  repairs: repairs,
  serviceType: formData.serviceType,
  appointment: formData.appointmentDate ? {
    date: formData.appointmentDate,
    time: formData.appointmentTime,
    confirmedAt: null
  } : null,
  status: "pending_quote",
  totalQuotedPrice: totalPrice,
  totalActualPrice: null,
  additionalNotes: formData.additionalNotes,
  submittedAt: new Date(),
  updatedAt: new Date()
};

// Step 5: Insert the repair request
const insertResult = db.repair_requests.insertOne(repairRequest);
const requestId = insertResult.insertedId;

print("Repair request created with ID: " + requestId);

// Step 6: Update appointment slot if booked
if (formData.appointmentDate) {
  const slotUpdateResult = db.appointment_slots.updateOne(
    {
      date: formData.appointmentDate,
      time: formData.appointmentTime,
      currentBookings: { $lt: "$maxCapacity" }
    },
    {
      $inc: { currentBookings: 1 },
      $push: {
        bookedBy: {
          requestId: requestId,
          customerEmail: formData.email,
          bookedAt: new Date()
        }
      }
    }
  );
  
  if (slotUpdateResult.modifiedCount === 1) {
    print("Appointment slot reserved successfully");
  } else {
    print("WARNING: Could not reserve appointment slot (may be full)");
  }
}

// ============================================================================
// ADDITIONAL USEFUL QUERIES
// ============================================================================

print("\n========================================");
print("Additional Useful Queries");
print("========================================\n");

// Get all pending repair requests
print("--- Pending repair requests ---");
db.repair_requests.find(
  { status: { $in: ["pending_quote", "quoted", "confirmed"] } },
  {
    _id: 1,
    "customer.firstName": 1,
    "customer.lastName": 1,
    "customer.email": 1,
    "device.brand": 1,
    "device.model": 1,
    serviceType: 1,
    status: 1,
    totalQuotedPrice: 1,
    submittedAt: 1
  }
).sort({ submittedAt: -1 }).pretty();

// Get today's appointments
print("\n--- Today's appointments ---");
const todayStart = new Date();
todayStart.setHours(0, 0, 0, 0);
const todayEnd = new Date();
todayEnd.setHours(23, 59, 59, 999);

db.repair_requests.find(
  {
    "appointment.date": {
      $gte: todayStart,
      $lte: todayEnd
    }
  },
  {
    _id: 1,
    "customer.firstName": 1,
    "customer.lastName": 1,
    "customer.phoneNumber": 1,
    "device.brand": 1,
    "device.model": 1,
    "appointment.time": 1,
    "repairs.serviceName": 1,
    status: 1
  }
).sort({ "appointment.time": 1 }).pretty();

// Get complete details of a specific repair request
print("\n--- Complete repair request details ---");
db.repair_requests.findOne(
  { "customer.email": "john.smith@email.com" }
).pretty();

// Get all requests by customer email
print("\n--- All requests by customer ---");
db.repair_requests.find(
  { "customer.email": "emma.j@email.com" }
).sort({ submittedAt: -1 }).pretty();

// Get repair statistics by device brand
print("\n--- Repair statistics by brand ---");
db.repair_requests.aggregate([
  {
    $group: {
      _id: "$device.brand",
      totalRepairs: { $sum: 1 },
      totalRevenue: { $sum: "$totalActualPrice" },
      avgPrice: { $avg: "$totalQuotedPrice" }
    }
  },
  {
    $sort: { totalRepairs: -1 }
  }
]).pretty();

// Get most common repairs
print("\n--- Most common repairs ---");
db.repair_requests.aggregate([
  { $unwind: "$repairs" },
  {
    $group: {
      _id: "$repairs.serviceName",
      count: { $sum: 1 },
      avgPrice: { $avg: "$repairs.quotedPrice" }
    }
  },
  {
    $sort: { count: -1 }
  }
]).pretty();

// Update repair status
print("\n--- Update repair status ---");
db.repair_requests.updateOne(
  { _id: ObjectId("...") }, // Replace with actual ID
  {
    $set: {
      status: "completed",
      totalActualPrice: NumberDecimal("89.99"),
      updatedAt: new Date()
    }
  }
);

// ============================================================================
// TRANSACTION EXAMPLE (for multi-document operations)
// ============================================================================

print("\n========================================");
print("Transaction Example");
print("========================================\n");

/*
// This would be used in a replica set or sharded cluster
const session = db.getMongo().startSession();
session.startTransaction();

try {
  // Insert repair request
  const result = session.getDatabase("repair_shop").repair_requests.insertOne({
    // ... document data
  });
  
  const requestId = result.insertedId;
  
  // Update appointment slot
  session.getDatabase("repair_shop").appointment_slots.updateOne(
    { date: appointmentDate, time: appointmentTime },
    { 
      $inc: { currentBookings: 1 },
      $push: { 
        bookedBy: { 
          requestId: requestId,
          customerEmail: email,
          bookedAt: new Date()
        }
      }
    }
  );
  
  // Commit the transaction
  session.commitTransaction();
  print("Transaction committed successfully");
  
} catch (error) {
  // Abort transaction on error
  session.abortTransaction();
  print("Transaction aborted: " + error);
} finally {
  session.endSession();
}
*/
