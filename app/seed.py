import random
import logging
from datetime import datetime, timedelta, date
from app.database import SessionLocal
from app.models import (
    Customer, Vehicle, WorkOrder, WorkOrderItem, Part, PartTransaction,
    Technician, Invoice, ScrapPickup, ScrapInventory, ScrapVendor,
    PurchaseOrder, PurchaseOrderItem, Lead, Alert, Schedule, ServiceReminder
)
from app.models.templates import (
    TemplateCategory, WorkflowTemplate, SubscriptionPlan
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
                qty = random.randint(1,3)
                wop = WorkOrderItem(
                    work_order_id=wo.id, description=part.name,
                    part_used=part.name, quantity=qty,
                    unit_price=part.price,
                    total_price=round(qty * part.price, 2),
                    is_labor=False,
                )
                db.add(wop)
                part.quantity = max(0, part.quantity - qty)
        db.flush()

        # Invoices
        for wo in [w for w in work_orders if w.status == "Completed"][:20]:
            inv_items = db.query(WorkOrderItem).filter(WorkOrderItem.work_order_id == wo.id).all()
            items_total = sum(ip.quantity * ip.unit_price for ip in inv_items)
            labor = wo.estimated_hours * 85
            inv_subtotal = items_total + labor
            inv_subtotal = max(inv_subtotal, 50)
            inv_total = round(inv_subtotal * 1.0825, 2)
            inv = Invoice(
                invoice_number=f"INV-{random.randint(1000,9999)}",
                work_order_id=wo.id,
                subtotal=round(inv_subtotal, 2),
                tax_rate=0.0825,
                tax_amount=round(inv_subtotal * 0.0825, 2),
                total_amount=inv_total,
                amount_paid=inv_total if random.random() > 0.3 else 0,
                status=random.choice(["Paid","Paid","Paid","Pending","Overdue"]),
                created_at=wo.completed_at or datetime.now(),
            )
            db.add(inv)
        db.flush()

        # Scrap vendors
        vendors = []
        vendor_names = ["Steel Dynamics", "Nucor Corp", "Crown Metal", "SIMS Metal", "David J. Joseph"]
        for vname in vendor_names:
            sv = ScrapVendor(
                name=vname,
                contact_person=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                material_types=random.choice(METALS),
            )
            db.add(sv)
            vendors.append(sv)
        db.flush()

        # Scrap pickups
        for i in range(20):
            sp = ScrapPickup(
                vendor_id=random.choice(vendors).id,
                pickup_date=datetime.now().date() + timedelta(days=random.randint(-30,14)),
                material_type=random.choice(METALS),
                weight_kg=round(random.uniform(2,227),1),
                price_per_kg=round(random.uniform(0.33,9.90),2),
                total_payout=0,
                location=random.choice(["Main Yard","Yard B","Customer Site"]),
                status=random.choice(["Completed","Completed","Completed","Scheduled","Cancelled"]),
                notes=f"{'Large load' if random.random()>0.7 else ''}",
            )
            sp.total_payout = round(sp.weight_kg * sp.price_per_kg, 2)
            db.add(sp)
        db.flush()

        # Scrap inventory
        for metal in METALS[:6]:
            si = ScrapInventory(
                material_type=metal,
                weight_kg=round(random.uniform(23,907),1),
                estimated_value=round(random.uniform(50,5000),2),
                notes=f"{metal} inventory from multiple pickups",
            )
            db.add(si)
        db.flush()

        # Purchase orders
        for i in range(8):
            po = PurchaseOrder(
                po_number=f"PO-{random.randint(1000,9999)}",
                supplier=random.choice(["Steel Dynamics","Nucor Corp","Crown Metal","SIMS Metal"]),
                status=random.choice(["Pending","Sent","Approved","Received"]),
                order_date=datetime.now().date() - timedelta(days=random.randint(1,45)),
                received_date=datetime.now().date() + timedelta(days=random.randint(1,30)) if random.random() > 0.5 else None,
                notes=f"Order for {random.choice(METALS[:5])}",
            )
            db.add(po)
            db.flush()
            for j in range(random.randint(1,3)):
                poi = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    part_id=random.choice(parts).id if parts else None,
                    part_name=f"{random.choice(METALS)} batch",
                    quantity_ordered=random.randint(10,100),
                    quantity_received=random.randint(0,100) if po.status == "Received" else 0,
                    unit_cost=round(random.uniform(0.50,5.00),2),
                    total_cost=0,
                )
                poi.total_cost = round(poi.quantity_ordered * poi.unit_cost, 2)
                db.add(poi)
        db.flush()

        # Leads
        for i in range(10):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            lead = Lead(
                name=f"{fn} {ln}",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                email=f"lead{i}@email.com",
                source=random.choice(LEAD_SOURCES),
                status=random.choice(LEAD_STATUSES),
                interest=random.choice(["brake repair","oil change","engine work","AC repair","scrap pickup"]),
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
            a = Alert(alert_type=atype, title=title, message=msg, severity=atype, related_type=rtype, related_id=rid, is_read=False)
            db.add(a)

        db.commit()
        logger.info("Demo data seeded: 20 customers, 20+ vehicles, 6 techs, 30 parts, 30 work orders, invoices, 20 scrap pickups, 8 POs, 10 leads, 5 alerts")

    except Exception as e:
        db.rollback()
        logger.exception("Failed to seed demo data")
    finally:
        db.close()


def seed_template_data():
    db = SessionLocal()
    try:
        if db.query(WorkflowTemplate).count() > 0:
            logger.info("Template data already exists, skipping seed")
            return

        logger.info("Seeding template marketplace data...")

        # --- Subscription Plans ---
        plans_data = [
            ("Starter", "starter", 29.00, 290.00, "free", 1,
             ["Access to free templates", "Basic workflow support", "Email notifications"]),
            ("Pro", "pro", 79.00, 790.00, "pro", 5,
             ["All Starter features", "Pro workflow templates", "Priority support", "Custom branding", "API access"]),
            ("Enterprise", "enterprise", 199.00, 1990.00, "all", -1,
             ["All Pro features", "Enterprise templates", "Dedicated account manager", "Custom integrations", "Unlimited users", "SLA guarantee"]),
        ]
        plans = {}
        for name, slug, monthly, yearly, access, max_users, features in plans_data:
            p = SubscriptionPlan(
                name=name, slug=slug, description=f"{name} plan for shops",
                price_monthly=monthly, price_yearly=yearly,
                template_access=access, max_users=max_users,
                features=features, is_active=True,
                sort_order=len(plans),
            )
            db.add(p)
            plans[slug] = p
        db.flush()

        # --- Template Categories ---
        cats_data = [
            ("Diagnostics", "diagnostics", "bi-search", "Engine, electrical, and system diagnostics", 1),
            ("Maintenance", "maintenance", "bi-tools", "Oil changes, fluid services, and preventive maintenance", 2),
            ("Repair Workflows", "repair", "bi-wrench", "Brake, transmission, suspension, and engine repair", 3),
            ("Scrap Metal", "scrap", "bi-recycle", "Pickup scheduling, grading, and pricing templates", 4),
            ("Estimates & Invoicing", "estimates", "bi-file-text", "Estimate templates, pricing guides, and invoice workflows", 5),
            ("Compliance & Safety", "compliance", "bi-shield-check", "DOT, emissions, OSHA, and environmental compliance", 6),
            ("Customer Service", "service", "bi-headset", "Follow-up, surveys, and customer communication", 7),
            ("Fleet Management", "fleet", "bi-truck-front", "Fleet inspections, scheduling, and contract management", 8),
        ]
        cats = {}
        for name, slug, icon, desc, order in cats_data:
            c = TemplateCategory(name=name, slug=slug, icon=icon, description=desc, sort_order=order)
            db.add(c)
            cats[slug] = c
        db.flush()

        # --- Workflow Templates ---
        tmpl_data = [
            # Diagnostics
            ("diagnostics", "Check Engine Light Diagnostic", "check-engine-diagnostic",
             "Standardized process for diagnosing check engine lights with OBD-II scanning and code interpretation.",
             "Follow this step-by-step workflow when a customer arrives with a check engine light. Covers OBD-II scanning, code interpretation, visual inspection, and repair recommendation.",
             ["Connect OBD-II scanner and retrieve diagnostic trouble codes", "Record all DTCs and freeze frame data",
              "Research TSBs (Technical Service Bulletins) for the codes found", "Perform visual inspection of related components",
              "Conduct targeted tests (compression, vacuum, electrical)", "Document findings and create repair estimate",
              "Present findings to customer with repair options"],
             ["OBD-II scanner is charged and functional", "DTC reference database is accessible", "Repair order is open",
              "Vehicle information is recorded", "Customer contact info is confirmed"],
             "45 min", "Intermediate", "diagnostics,OBD-II,check engine,diagnostic", "pro", 14.99, 127, 4.6, 18, True),
            ("diagnostics", "No-Start Diagnostic", "no-start-diagnostic",
             "Systematic no-start diagnosis covering battery, starter, fuel, and ignition systems.",
             "Use this template when a vehicle won't start. Methodically eliminates causes from battery to fuel delivery.",
             ["Verify customer complaint and attempt to reproduce", "Check battery voltage and load test",
              "Test starter circuit (solenoid, relay, wiring)", "Check fuel pressure and delivery",
              "Test ignition system (spark, coils, plugs)", "Check for immobilizer/anti-theft issues",
              "Document diagnosis and recommend repair"],
             ["Battery load tester available", "Fuel pressure gauge available", "Multimeter ready",
              "Work order created", "Customer notified of diagnostic fee"],
             "1 hr", "Advanced", "diagnostics,no-start,battery,starter,fuel", "pro", 19.99, 89, 4.5, 12, False),
            ("diagnostics", "Electrical Gremlin Hunt", "electrical-diagnostic",
             "Methodical electrical diagnosis for intermittent issues, parasitic draws, and wiring faults.",
             "For hard-to-find electrical problems. Uses systematic isolation technique to find shorts, opens, and parasitic draws.",
             ["Gather detailed symptom description from customer", "Review wiring diagrams for affected circuits",
              "Perform voltage drop tests on ground and power circuits", "Check for parasitic draw (wait for modules to sleep)",
              "Use thermal camera to identify hot spots", "Perform wiggle test on suspect connectors",
              "Document root cause and repair plan"],
             ["Wiring diagrams accessible", "Multimeter and test light ready", "Thermal camera available",
              "Parasitic draw test setup", "Vehicle in diagnostic bay"],
             "2 hr", "Advanced", "electrical,parasitic draw,wiring,diagnostics", "enterprise", 29.99, 54, 4.7, 9, False),

            # Maintenance
            ("maintenance", "Full Synthetic Oil Change", "oil-change",
             "Complete oil change workflow with multi-point inspection checklist.",
             "Standard operating procedure for a full synthetic oil change including drain, filter, fill, and 25-point inspection.",
             ["Verify vehicle info and recommended oil spec", "Lift vehicle and place on stands",
              "Drain old oil completely (10 min minimum)", "Remove and replace oil filter",
              "Inspect drain plug washer, replace if needed", "Lower vehicle and fill with correct oil amount",
              "Check all fluid levels (coolant, brake, power steering, washer)",
              "Perform 25-point inspection checklist", "Reset maintenance light", "Update service records and set next reminder"],
             ["Correct oil spec confirmed", "New oil filter in stock", "Oil drain pan ready",
              "Lift is operational", "Service reminder system ready"],
             "30 min", "Beginner", "maintenance,oil change,synthetic,inspection", "free", 0, 342, 4.8, 45, True),
            ("maintenance", "Coolant Flush Service", "coolant-flush",
             "Complete coolant flush and refill procedure with system pressure test.",
             "Full coolant system service including drain, flush, pressure test, and refill with correct coolant mix.",
             ["Connect pressure tester and test system integrity", "Drain coolant from petcock and block drains",
              "Flush system with clean water until clear", "Inspect hoses and clamps while system is empty",
              "Replace thermostat if scheduled", "Fill with correct coolant-to-water mix (50/50)",
              "Bleed air from system using bleeder valves", "Pressure test again to confirm no leaks",
              "Road test and verify operating temperature"],
             ["Flush machine charged", "Correct coolant type in stock", "Pressure tester available",
              "Thermostat on hand if needed", "Work order authorized"],
             "1.5 hr", "Intermediate", "maintenance,coolant,flush,cooling system", "pro", 12.99, 198, 4.4, 22, False),
            ("maintenance", "Transmission Service", "transmission-service",
             "Automatic transmission fluid drain, filter, and refill procedure.",
             "Complete transmission service for automatic transmissions including pan drop, filter change, and fluid refill.",
             ["Verify transmission type and fluid spec", "Lift vehicle and place on level surface",
              "Remove transmission pan bolts carefully", "Drain fluid and remove old filter",
              "Clean pan and replace magnet", "Install new filter and gasket",
              "Reinstall pan with correct torque sequence", "Refill with specified fluid type and amount",
              "Cycle through all gears and check level", "Road test and verify shift quality"],
             ["Transmission spec confirmed", "New filter kit in stock", "Correct fluid type available",
              "Torque wrench calibrated", "Work order authorized"],
             "2 hr", "Intermediate", "maintenance,transmission,fluid,filter", "pro", 16.99, 167, 4.5, 15, False),

            # Repair
            ("repair", "Front Brake Job", "brake-job",
             "Complete front brake pad and rotor replacement with hardware and fluid service.",
             "Standard brake job template covering pad replacement, rotor resurfacing/replacement, hardware kit, and brake fluid check.",
             ["Verify brake specification and parts availability", "Loosen lug nuts and lift vehicle",
              "Remove caliper and bracket", "Remove old pads and inspect hardware",
              "Measure rotor thickness and runout", "Replace or resurface rotors as needed",
              "Install new hardware kit", "Install new pads with anti-squeal compound",
              "Reinstall caliper and torque to spec", "Pump brakes to seat pads",
              "Road test and bed-in brakes", "Measure pad thickness and document"],
             ["Brake pads and rotors in stock", "Hardware kit available", "Brake cleaner ready",
              "Torque wrench available", "Work order authorized with estimate"],
             "1.5 hr", "Beginner", "repair,brakes,pads,rotors,front", "free", 0, 287, 4.9, 52, True),
            ("repair", "Serpentine Belt Replacement", "serpentine-belt",
             "Serpentine belt removal, tensioner inspection, and replacement procedure.",
             "Complete serpentine belt replacement including tensioner inspection and alignment check.",
             ["Locate belt routing diagram", "Check tensioner operation and travel",
              "Release tensioner and remove old belt", "Inspect all pulleys for wear/noise",
              "Route new belt per diagram", "Verify belt alignment on all pulleys",
              "Apply tension and verify proper tensioner engagement",
              "Start engine and check for noise/misalignment"],
             ["New belt part number verified", "Belt routing diagram available", "Pulley tools ready",
              "Work order authorized"],
             "45 min", "Beginner", "repair,belt,serpentine,tensioner", "free", 0, 178, 4.7, 28, False),
            ("repair", "Rear Shock/Strut Replacement", "shock-strut",
             "Rear shock or strut replacement procedure with alignment check recommendation.",
             "Step-by-step rear shock/strut replacement including spring compression safety and post-repair alignment check.",
             ["Verify correct parts for vehicle", "Raise vehicle and remove rear wheels",
              "Support axle/spring assembly", "Remove upper and lower mounting bolts",
              "Compress spring if replacing strut assembly", "Install new shock/strut",
              "Torque all bolts to manufacturer spec", "Reinstall wheels and lower vehicle",
              "Recommend 4-wheel alignment", "Road test for noise and handling"],
             ["New shocks/struts on hand", "Spring compressor available (if strut)", "Jack stands rated for vehicle",
              "Torque specs available", "Work order authorized"],
             "2 hr", "Intermediate", "repair,suspension,shock,strut,rear", "pro", 18.99, 112, 4.3, 14, False),
            ("repair", "AC System Recharge & Leak Test", "ac-recharge",
             "Complete AC service with evacuate, recharge, dye test, and performance verification.",
             "Full AC service procedure from recovery to performance test, including UV dye leak detection.",
             ["Connect manifold gauge set and read pressures", "Recover existing refrigerant",
              "Connect vacuum pump and evacuate system (30 min minimum)",
              "Perform UV dye injection", "Charge system with correct refrigerant amount",
              "Run system at max cool and verify vent temps",
              "Inspect with UV light for dye leaks",
              "Document pressures, temperatures, and findings"],
             ["Manifold gauge set ready", "Recovery machine charged", "Vacuum pump operational",
              "UV dye and light available", "Correct refrigerant in stock", "Work order authorized"],
             "1.5 hr", "Intermediate", "repair,AC,HVAC,refrigerant,leak", "pro", 15.99, 145, 4.4, 19, False),

            # Scrap
            ("scrap", "Scrap Pickup Scheduling", "scrap-pickup",
             "Standard workflow for scheduling and completing a scrap metal pickup from a customer location.",
             "End-to-end pickup workflow from customer request to load confirmation and payment.",
             ["Receive pickup request (phone/web/form)", "Verify customer info and pickup address",
              "Schedule pickup date and time window", "Confirm metal types and estimated weight",
              "Dispatch truck and crew", "Arrive and inspect/grade materials on-site",
              "Weigh load on truck scale", "Calculate payment based on current rates",
              "Issue payment and receipt", "Update inventory and CRM records"],
             ["Customer contact confirmed", "Truck and crew scheduled", "Current metal pricing loaded",
              "Payment method ready", "CRM pickup record created"],
             "2 hr", "Beginner", "scrap,pickup,scheduling,grading", "free", 0, 234, 4.6, 31, True),
            ("scrap", "Scrap Metal Grading Guide", "scrap-grading",
             "Reference workflow for properly grading and pricing different scrap metal types.",
             "Use this template when evaluating scrap metal quality and determining pricing tier for each load.",
             ["Visually identify metal type (color, weight, magnet test)",
              "Sort metals into grade categories", "Check for contamination (plastic, rubber, paint)",
              "Weigh each grade separately", "Apply current market pricing per grade",
              "Calculate total value", "Document with photos for dispute resolution",
              "Provide customer with itemized receipt"],
             ["Grading scale reference chart", "Scale calibrated", "Current pricing sheet loaded",
              "Photo documentation setup"],
             "30 min", "Beginner", "scrap,grading,pricing,evaluation", "free", 0, 189, 4.5, 24, False),
            ("scrap", "Scrap Inventory Reconciliation", "scrap-reconciliation",
             "Monthly reconciliation of scrap inventory vs purchase records and sales.",
             "Template for monthly inventory count, variance analysis, and reconciliation reporting.",
             ["Generate purchase log for the month", "Generate sales/shipping log for the month",
              "Physically count each metal type on hand", "Record weights by location",
              "Calculate expected vs actual inventory", "Investigate variances over threshold",
              "Write off damaged/lost material with approval",
              "Generate reconciliation report", "Update pricing based on current market"],
             ["Purchase records accessible", "Sales records accessible", "Scale available for recount",
              "Previous month's reconciliation", "Management approval for write-offs"],
             "3 hr", "Intermediate", "scrap,inventory,reconciliation,accounting", "pro", 24.99, 67, 4.2, 8, False),

            # Estimates
            ("estimates", "Collision Repair Estimate", "collision-estimate",
             "Detailed collision damage estimate template with photo documentation.",
             "Use for any collision repair estimate. Includes damage assessment, parts list, labor times, and photo requirements.",
             ["Document customer description of incident", "Photograph all damage (exterior, interior, undercarriage)",
              "Perform initial damage assessment", "Identify hidden damage areas (pull test, measure frame)",
              "Look up parts pricing and availability", "Estimate labor hours per operation",
              "Add paint time and materials", "Include sublet operations if needed",
              "Present estimate with options (OEM/aftermarket/reman)",
              "Get customer authorization and signature"],
             ["Estimate software loaded", "Camera for photos", "Parts catalog accessible",
              "Labor time guide available", "Customer on-site for authorization"],
             "1 hr", "Intermediate", "estimates,collision,body,damage,photo", "pro", 9.99, 156, 4.7, 21, False),
            ("estimates", "Pre-Purchase Inspection Template", "pre-purchase-inspection",
             "Comprehensive pre-purchase inspection checklist for used vehicle buyers.",
             "Full vehicle inspection template covering mechanical, electrical, body, and safety systems.",
             ["Record vehicle info (VIN, mileage, year/make/model)",
              "Exterior walk-around (paint, dents, rust, glass)",
              "Under-hood inspection (fluids, belts, hoses, leaks)",
              "Undercarriage inspection (frame, suspension, exhaust)",
              "Interior inspection (electronics, seats, HVAC, warning lights)",
              "Test drive (brakes, steering, transmission, noises)",
              "OBD-II scan for stored/history codes",
              "Photograph all findings", "Generate report with severity ratings",
              "Present report to customer with recommendations"],
             ["OBD-II scanner ready", "Lift or pit access", "Inspection checklist printed",
              "Report template loaded", "Camera for documentation"],
             "2 hr", "Intermediate", "estimates,inspection,pre-purchase,used vehicle", "pro", 11.99, 134, 4.8, 16, False),

            # Compliance
            ("compliance", "DOT Inspection Checklist", "dot-inspection",
             "Federal DOT annual inspection checklist for commercial vehicles.",
             "Complete FMCSA DOT annual vehicle inspection with all required items documented.",
             ["Verify vehicle registration and insurance docs", "Inspect brakes (pads, rotors, lines, slack adjusters)",
              "Check steering and suspension components", "Inspect tires (tread depth, condition, inflation)",
              "Check lights and reflective devices", "Inspect exhaust system and emissions",
              "Test all safety equipment (fire extinguisher, triangles, spare fuses)",
              "Check mirrors, windshield, wipers", "Inspect coupling devices if applicable",
              "Complete CVSA decal and inspection report", "File report with DMV if required"],
             ["DOT inspection form loaded", "CVSA decal available", "All tools ready",
              "Previous inspection report on file", "Vehicle in inspection bay"],
             "1.5 hr", "Intermediate", "compliance,DOT,inspection,federal,commercial", "pro", 19.99, 98, 4.6, 11, False),
            ("compliance", "Emissions Testing Prep", "emissions-prep",
             "Pre-test preparation workflow for emissions inspections.",
             "Prepare vehicle for emissions testing to maximize pass rate. Catches common failures before the test.",
             ["Check for check engine light (must be off)", "Scan for pending codes",
              "Verify catalytic converter operation", "Check O2 sensor response times",
              "Inspect EVAP system for leaks", "Verify PCV system operation",
              "Check EGR function", "Perform drive cycle readiness if needed",
              "Document all pre-test results", "Recommend repairs if issues found"],
             ["OBD-II scanner with readiness monitors", " exhaust gas analyzer if available",
              "Service bay ready", "Work order created"],
             "45 min", "Beginner", "compliance,emissions,EPA,OBD-II,preparation", "free", 0, 145, 4.4, 17, False),
            ("compliance", "OSHA Shop Safety Audit", "osha-audit",
             "Annual OSHA compliance audit template for auto repair shops.",
             "Self-audit checklist covering all major OSHA requirements for automotive repair facilities.",
             ["Review written hazard communication program", "Verify SDS sheets are current and accessible",
              "Check fire extinguisher inspection tags", "Inspect eyewash/shower stations",
              "Verify PPE availability and usage", "Check chemical storage compliance",
              "Inspect lifts and equipment certification", "Review employee training records",
              "Check ventilation and air quality", "Document findings and corrective actions"],
             ["OSHA checklist printed", "Previous audit on file", "Access to all shop areas",
              "Training records available", "Management walk-through scheduled"],
             "4 hr", "Advanced", "compliance,OSHA,safety,audit,shop", "enterprise", 34.99, 42, 4.3, 6, False),

            # Customer Service
            ("service", "Post-Repair Follow-Up", "post-repair-followup",
             "Standardized follow-up workflow after repair completion to ensure customer satisfaction.",
             "Automated follow-up process covering call, survey, and review request timeline.",
             ["Send completion notification (same day)", "Make follow-up call at 3 days",
              "Send satisfaction survey at 7 days", "Request online review at 14 days",
              "Log all customer responses in CRM", "Escalate any complaints to manager",
              "Update customer loyalty tier if applicable", "Schedule next service reminder"],
             ["Customer contact info verified", "Survey template ready", "Review link generated",
              "CRM follow-up task created"],
             "15 min", "Beginner", "service,follow-up,satisfaction,survey,review", "free", 0, 267, 4.8, 38, True),
            ("service", "Customer Complaint Resolution", "complaint-resolution",
             "Structured complaint handling workflow with escalation paths.",
             "Use when a customer has a complaint. Follows AIDAR model (Apologize, Identify, Develop, Act, Review).",
             ["Receive complaint and document in detail", "Apologize sincerely for the inconvenience",
              "Identify the root cause of the issue", "Develop resolution options",
              "Present options to customer with recommendation", "Implement chosen resolution",
              "Follow up within 48 hours", "Document resolution and lessons learned",
              "Update procedures if systemic issue found"],
             ["Complaint form available", "Manager on standby for escalation", "Previous service records accessible",
              "Resolution authority levels defined"],
             "1 hr", "Intermediate", "service,complaint,resolution,customer,escalation", "pro", 7.99, 112, 4.5, 14, False),

            # Fleet
            ("fleet", "Fleet Vehicle Inspection", "fleet-inspection",
             "Standardized fleet vehicle inspection for commercial fleet accounts.",
             "Monthly/quarterly fleet inspection template covering all DOT and maintenance items.",
             ["Assign vehicle to inspection work order", "Perform exterior walk-around",
              "Check all fluid levels and conditions", "Inspect tires and document tread depths",
              "Test all lights, signals, and warning systems", "Check brakes (pad thickness, rotor condition)",
              "Inspect suspension and steering components", "Check undercarriage for leaks and damage",
              "Scan for diagnostic trouble codes", "Generate inspection report with findings",
              "Create work orders for any required repairs", "Send report to fleet manager"],
             ["Fleet account set up in system", "Inspection checklist loaded", "Tread depth gauge ready",
              "OBD-II scanner ready", "Fleet manager contact info on file"],
             "1.5 hr", "Intermediate", "fleet,inspection,commercial,DOT,maintenance", "pro", 22.99, 89, 4.6, 11, False),
            ("fleet", "Fleet Service Scheduling", "fleet-scheduling",
             "Recurring service scheduling template for fleet maintenance contracts.",
             "Manage recurring service intervals for fleet vehicles based on mileage or time.",
             ["Pull fleet roster and service history", "Identify vehicles due for service",
              "Generate service reminders for fleet contacts", "Schedule bay time for fleet batch service",
              "Pre-order parts for scheduled services", "Confirm appointments with fleet manager",
              "Execute services per manufacturer intervals", "Update mileage tracking",
              "Generate invoice per fleet contract terms", "File service records for DOT compliance"],
             ["Fleet roster in CRM", "Service interval schedule defined", "Parts ordering system ready",
              "Fleet contract terms on file"],
             "2 hr", "Intermediate", "fleet,scheduling,maintenance,contract,recurring", "pro", 21.99, 76, 4.4, 9, False),

            # Estimates
            ("estimates", "Parts Markup Calculator", "parts-markup",
             "Standard parts markup guide with tiered pricing by category and supplier.",
             "Reference template for consistent parts markup across the shop. Includes category-specific rates.",
             ["Identify part category (mechanical, electrical, body, etc.)",
              "Look up standard markup rate for category", "Apply tiered pricing for high-volume suppliers",
              "Calculate retail price from cost", "Verify against market pricing",
              "Apply fleet discount if applicable", "Document pricing decision",
              "Update parts database if needed"],
             ["Markup rate schedule current", "Parts cost database accessible", "Market pricing reference",
              "Fleet discount schedule available"],
             "15 min", "Beginner", "estimates,pricing,markup,parts,calculator", "free", 0, 201, 4.3, 22, False),

            # Maintenance
            ("maintenance", "Tire Rotation & Balance", "tire-rotation",
             "Complete tire rotation, balance, and pressure service workflow.",
             "Standard tire service including rotation pattern, wheel balance, and TPMS check.",
             ["Verify tire sizes and rotation pattern", "Check current tread depth all around",
              "Lift vehicle and remove wheels", "Rotate tires per manufacturer spec",
              "Mount on balancer and check balance", "Add/remove weights as needed",
              "Check TPMS sensors and battery status", "Set correct tire pressure",
              "Reinstall wheels and torque lug nuts", "Perform road test and verify no vibration"],
             ["Wheel balancer operational", "Torque wrench available", "TPMS tool ready",
              "Correct tire pressure spec", "Work order created"],
             "45 min", "Beginner", "maintenance,tires,rotation,balance,TPMS", "free", 0, 289, 4.7, 34, False),

            # Repair
            ("repair", "Engine Timing Belt Service", "timing-belt",
             "Timing belt replacement with water pump and tensioner service.",
             "Major service template for timing belt replacement including all associated components.",
             ["Verify engine specs and belt routing diagram", "Drain coolant if doing water pump",
              "Remove access covers and components", "Set engine to TDC on #1 cylinder",
              "Mark timing marks on cam and crank", "Remove old belt and tensioner",
              "Inspect idler pulleys and water pump", "Install new tensioner, idler, and belt",
              "Verify timing marks align after rotation", "Reinstall components and refill coolant",
              "Start engine and verify smooth operation", "Document mileage and next service interval"],
             ["Timing belt kit in stock", "Water pump available", "Torque wrench calibrated",
              "Service manual with torque specs", "Work order authorized (high-value job)"],
             "5 hr", "Advanced", "repair,timing belt,water pump,engine,major", "enterprise", 49.99, 67, 4.8, 8, False),
        ]

        for (cat_slug, name, slug, desc, long_desc, steps, checklist,
             est_time, difficulty, tags, tier, price, purchases, rating,
             rating_count, featured) in tmpl_data:
            cat = cats.get(cat_slug)
            if not cat:
                continue
            t = WorkflowTemplate(
                category_id=cat.id, name=name, slug=slug,
                description=desc, long_description=long_desc,
                steps=steps, checklist=checklist,
                estimated_time=est_time, difficulty=difficulty,
                tags=tags, tier=tier, price=price,
                purchase_count=purchases, rating=rating,
                rating_count=rating_count, is_featured=featured,
                is_active=True,
            )
            db.add(t)
        db.flush()

        db.commit()
        logger.info("Template data seeded: 3 plans, 8 categories, 24 templates")

    except Exception as e:
        db.rollback()
        logger.exception("Failed to seed template data")
    finally:
        db.close()
