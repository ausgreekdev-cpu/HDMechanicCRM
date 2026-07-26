import random
import logging
from datetime import datetime, timedelta, date
from app.database import SessionLocal
from app.models import (
    Customer, Vehicle, WorkOrder, WorkOrderPart, Part, PartTransaction,
    Technician, Invoice, InvoiceItem, ScrapPickup, ScrapInventory,
    PurchaseOrder, Lead, Alert, Schedule, ServiceReminder
)
from app.auth import hash_password

logger = logging.getLogger(__name__)

FIRST_NAMES = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
               "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica",
               "Thomas","Sarah","Charles","Karen","Daniel","Lisa","Matthew","Nancy"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
              "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
              "Thomas","Taylor","Moore","Jackson","Martin"]
STREETS = ["Oak St","Main St","Elm Ave","Pine Rd","Cedar Ln","Maple Dr","1st Ave","2nd St","Broadway","5th St"]
CITIES = ["Austin","Houston","Dallas","San Antonio","Fort Worth","El Paso","Arlington","Corpus Christi"]
METALS = ["Copper","Aluminum","Steel","Brass","Stainless Steel","Iron","Zinc","Lead"]
SPECIALTIES = ["Engine","Transmission","Brakes","Electrical","Suspension","Exhaust","AC/HVAC","General"]

VEHICLE_DATA = [
    ("Toyota",["Camry","Corolla","RAV4","Tacoma","Highlander"]),
    ("Honda",["Civic","Accord","CR-V","Pilot","Fit"]),
    ("Ford",["F-150","Escape","Explorer","Mustang","Focus"]),
    ("Chevrolet",["Silverado","Malibu","Equinox","Tahoe","Cruze"]),
    ("Nissan",["Altima","Sentra","Rogue","Pathfinder","Frontier"]),
    ("Hyundai",["Elantra","Sonata","Tucson","Santa Fe","Accent"]),
    ("BMW",["3 Series","5 Series","X3","X5","7 Series"]),
    ("Mercedes-Benz",["C-Class","E-Class","GLC","GLE","A-Class"]),
]

LEAD_SOURCES = ["Website","Phone","Walk-in","Referral","Google","Facebook","Yelp"]
LEAD_STATUSES = ["New","Contacted","Qualified","Proposal","Won","Lost"]
PAYMENT_METHODS = ["Cash","Check","Credit Card","Debit Card","Venmo","Square","Zelle","PayPal"]
URGENCY = ["Low","Medium","High","Emergency"]


def seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(Customer).count() > 0:
            logger.info("Demo data already exists, skipping seed")
            return

        logger.info("Seeding demo data...")

        # Customers
        customers = []
        for i in range(20):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            c = Customer(
                first_name=fn, last_name=ln,
                email=f"{fn.lower()}.{ln.lower()}@email.com",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                address=f"{random.randint(100,9999)} {random.choice(STREETS)}",
                city=random.choice(CITIES), state="TX",
                notes=f"Customer since {random.randint(2020,2025)}",
                customer_type=random.choice(["Residential","Commercial","Fleet"]),
                created_at=datetime.now() - timedelta(days=random.randint(30,730))
            )
            db.add(c)
            customers.append(c)
        db.flush()

        # Vehicles
        vehicles = []
        for c in customers:
            make, models = random.choice(VEHICLE_DATA)
            v = Vehicle(
                customer_id=c.id, make=make, model=random.choice(models),
                year=random.randint(2010,2024),
                vin=f"{''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ0123456789', k=17))}",
                license_plate=f"{''.join(random.choices('ABCDEFGH', k=3))}-{random.randint(1000,9999)}",
                color=random.choice(["White","Black","Silver","Red","Blue","Gray","Navy"]),
                mileage=random.randint(5000,150000),
                created_at=c.created_at
            )
            db.add(v)
            vehicles.append(v)
        db.flush()

        # Technicians
        techs = []
        tech_names = [("Mike Johnson","lead"),("Sarah Chen","technician"),("Carlos Ruiz","technician"),
                      ("Dave Wilson","technician"),("Alex Kim","apprentice"),("Tom Brown","lead")]
        for name, role in tech_names:
            t = Technician(
                name=name, specialty=random.choice(SPECIALTIES),
                hourly_rate=random.uniform(25,65), is_active=True,
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
            )
            db.add(t)
            techs.append(t)
        db.flush()

        # Parts inventory
        parts = []
        part_data = [
            ("Oil Filter","Filter",8.99,25),("Air Filter","Filter",12.99,20),
            ("Brake Pads (Front)","Brake",34.99,15),("Brake Pads (Rear)","Brake",29.99,15),
            ("Brake Rotor","Brake",54.99,10),("Spark Plugs (Set)","Engine",19.99,30),
            ("Timing Belt","Engine",89.99,5),("Serpentine Belt","Engine",24.99,12),
            ("Coolant","Fluid",14.99,20),("Transmission Fluid","Fluid",18.99,15),
            ("Wiper Blades (Pair)","Exterior",16.99,25),("Battery","Electrical",129.99,8),
            ("Alternator","Electrical",189.99,4),("Starter Motor","Electrical",149.99,4),
            ("O2 Sensor","Engine",39.99,10),("Catalytic Converter","Exhaust",249.99,3),
            ("Fuel Pump","Fuel",119.99,5),("Water Pump","Cooling",79.99,6),
            ("AC Compressor","HVAC",299.99,3),("Radiator","Cooling",159.99,4),
            ("Headlight Assembly","Lighting",69.99,8),("Tail Light Assembly","Lighting",49.99,8),
            ("Spark Plug Wire Set","Electrical",34.99,10),("Clutch Kit","Transmission",199.99,4),
            ("Wheel Bearing","Suspension",59.99,8),("Tie Rod End","Suspension",39.99,10),
            ("Shock Absorber","Suspension",89.99,8),("Strut Assembly","Suspension",149.99,6),
            ("Gasket Set","Engine",44.99,10),("Piston Ring Set","Engine",79.99,5),
        ]
        for pn, cat, cost, qty in part_data:
            p = Part(
                part_number=f"P-{random.randint(10000,99999)}", name=pn,
                category=cat, cost=cost, price=round(cost * random.uniform(1.4,2.2),2),
                quantity=qty, min_quantity=max(3, qty // 4),
                supplier=f"AutoZone" if random.random()>0.5 else "O'Reilly",
                created_at=datetime.now() - timedelta(days=random.randint(1,180))
            )
            db.add(p)
            parts.append(p)
        db.flush()

        # Work Orders
        statuses = ["Pending","In Progress","Completed","On Hold"]
        wo_descs = [
            "Oil change and filter replacement","Full brake job - pads, rotors, fluid",
            "Engine diagnostic - check engine light","Transmission service",
            "AC recharge and leak repair","Suspension inspection and repair",
            "Battery replacement and charging system check","Timing belt replacement",
            "Coolant flush and thermostat replacement","Exhaust repair",
            "Wheel alignment and tire rotation","Electrical short diagnosis",
            "Starter motor replacement","Alternator replacement",
            "Fuel system cleaning","Radiator replacement",
            "Headlight restoration","Clutch replacement",
            "CV joint replacement","Power steering repair",
        ]
        work_orders = []
        for i in range(30):
            c = random.choice(customers)
            v = random.choice([v for v in vehicles if v.customer_id == c.id] or vehicles)
            tech = random.choice(techs)
            status = random.choice(statuses)
            wo = WorkOrder(
                customer_id=c.id, vehicle_id=v.id, technician_id=tech.id,
                description=random.choice(wo_descs),
                status=status, priority=random.choice(URGENCY),
                estimated_hours=round(random.uniform(0.5,8),1),
                actual_hours=round(random.uniform(0.5,8),1) if status == "Completed" else None,
                mileage=v.mileage + random.randint(0,5000),
                created_at=datetime.now() - timedelta(days=random.randint(0,90)),
                started_at=datetime.now() - timedelta(days=random.randint(0,60)) if status != "Pending" else None,
                completed_at=datetime.now() - timedelta(days=random.randint(0,30)) if status == "Completed" else None,
            )
            db.add(wo)
            work_orders.append(wo)
        db.flush()

        # Add parts to work orders
        for wo in work_orders[:20]:
            used = random.sample(parts, k=random.randint(1,4))
            for part in used:
                wop = WorkOrderPart(
                    work_order_id=wo.id, part_id=part.id,
                    quantity=random.randint(1,3),
                    unit_price=part.price
                )
                db.add(wop)
                part.quantity = max(0, part.quantity - wop.quantity)
        db.flush()

        # Invoices
        for wo in [w for w in work_orders if w.status == "Completed"][:20]:
            inv = Invoice(
                customer_id=wo.customer_id, work_order_id=wo.id,
                invoice_number=f"INV-{random.randint(10000,99999)}",
                subtotal=round(random.uniform(75,2500),2),
                tax=round(random.uniform(5,200),2),
                total=0,  # calculated
                payment_method=random.choice(PAYMENT_METHODS),
                status=random.choice(["Paid","Paid","Paid","Pending","Overdue"]),
                created_at=wo.completed_at or datetime.now(),
            )
            inv_items = db.query(WorkOrderPart).filter(WorkOrderPart.work_order_id == wo.id).all()
            items_total = sum(ip.quantity * ip.unit_price for ip in inv_items)
            labor = wo.estimated_hours * 85
            inv_subtotal = items_total + labor
            inv_subtotal = max(inv_subtotal, 50)
            inv_total = round(inv_subtotal * 1.0825, 2)
            inv = Invoice(
                invoice_number=f"INV-{random.randint(1000,9999)}",
                customer_id=wo.customer_id,
                subtotal=round(inv_subtotal, 2),
                tax=round(inv_subtotal * 0.0825, 2),
                total=inv_total,
                payment_method=random.choice(PAYMENT_METHODS),
                status=random.choice(["Paid","Paid","Paid","Pending","Overdue"]),
                created_at=wo.completed_at or datetime.now(),
            )
            db.add(inv)
            for ip in inv_items:
                ii = InvoiceItem(
                    invoice_id=inv.id, description=ip.part.name if ip.part else "Labor",
                    quantity=ip.quantity, unit_price=ip.unit_price,
                    total=round(ip.quantity * ip.unit_price, 2)
                )
                db.add(ii)
        db.flush()

        # Scrap pickups
        for i in range(20):
            sp = ScrapPickup(
                customer_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                address=f"{random.randint(100,9999)} {random.choice(STREETS)}, {random.choice(CITIES)}, TX",
                metal_type=random.choice(METALS),
                weight_lbs=round(random.uniform(5,500),1),
                price_per_lb=round(random.uniform(0.15,4.50),2),
                total_value=0,
                status=random.choice(["Scheduled","Completed","Completed","Cancelled"]),
                pickup_date=datetime.now().date() + timedelta(days=random.randint(-30,14)),
                notes=f"{'Large load' if random.random()>0.7 else ''}",
                created_at=datetime.now() - timedelta(days=random.randint(1,60))
            )
            sp.total_value = round(sp.weight_lbs * sp.price_per_lb, 2)
            db.add(sp)
        db.flush()

        # Scrap inventory
        for metal in METALS[:6]:
            si = ScrapInventory(
                metal_type=metal,
                quantity_lbs=round(random.uniform(50,2000),1),
                avg_cost_per_lb=round(random.uniform(0.20,3.50),2),
                location=random.choice(["Main Yard","Yard B","Warehouse"]),
                last_updated=datetime.now() - timedelta(days=random.randint(0,7))
            )
            db.add(si)
        db.flush()

        # Purchase orders
        for i in range(8):
            po = PurchaseOrder(
                po_number=f"PO-{random.randint(1000,9999)}",
                supplier=random.choice(["Steel Dynamics","Nucor Corp","Crown Metal","SIMS Metal"]),
                metal_type=random.choice(METALS[:5]),
                weight_lbs=round(random.uniform(500,5000),1),
                price_per_lb=round(random.uniform(0.25,4.00),2),
                total_amount=0,
                status=random.choice(["Draft","Sent","Approved","Received"]),
                created_at=datetime.now() - timedelta(days=random.randint(1,45)),
                expected_delivery=datetime.now().date() + timedelta(days=random.randint(1,30))
            )
            po.total_amount = round(po.weight_lbs * po.price_per_lb, 2)
            db.add(po)
        db.flush()

        # Leads
        for i in range(10):
            lead = Lead(
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                email=f"lead{i}@email.com",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                source=random.choice(LEAD_SOURCES),
                status=random.choice(LEAD_STATUSES),
                notes=f"Interested in {random.choice(['brake repair','oil change','engine work','AC repair','scrap pickup'])}",
                follow_up_date=date.today() + timedelta(days=random.randint(-5,14)),
                created_at=datetime.now() - timedelta(days=random.randint(1,60))
            )
            db.add(lead)
        db.flush()

        # Alerts
        alert_data = [
            ("warning","Low Stock","3 parts below minimum quantity","inventory",None),
            ("info","Scheduler Running","Background agents active","system",None),
            ("danger","Overdue Invoice","INV-2001 is 15 days overdue","finance",None),
            ("warning","Service Reminder","3 vehicles due for service","service",None),
            ("info","Scrap Price Alert","Copper price dropped 3%","scrap",None),
        ]
        for atype, title, msg, rtype, rid in alert_data:
            a = Alert(alert_type=atype, title=title, message=msg, related_type=rtype, related_id=rid, is_read=False)
            db.add(a)

        db.commit()
        logger.info("Demo data seeded: 20 customers, 20+ vehicles, 6 techs, 30 parts, 30 work orders, invoices, 20 scrap pickups, 8 POs, 10 leads, 5 alerts")

    except Exception as e:
        db.rollback()
        logger.exception("Failed to seed demo data")
    finally:
        db.close()
