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

            # --- Additional Diagnostics ---
            ("diagnostics", "Transmission Diagnostic", "transmission-diagnostic",
             "Diagnostic workflow for transmission shifting and slipping issues.",
             "Comprehensive transmission diagnostic covering fluid condition, pressure tests, and electronic diagnostics for smooth shifting resolution.",
             ["Verify customer complaint and driving conditions", "Check transmission fluid level and condition",
              "Scan for transmission-related DTCs", "Perform road test and document shift quality",
              "Check transmission cooler line pressures", "Inspect shift solenoids and wiring",
              "Evaluate torque converter operation", "Review service history for previous trans work",
              "Generate diagnostic report with repair recommendation", "Present findings to customer with estimate"],
             ["OBD-II scanner with transmission capability", "Transmission pressure gauge kit",
              "Known-good transmission fluid sample", "Vehicle service history available",
              "Road test route planned"],
             "1.5 hr", "Advanced", "diagnostics,transmission,shifting,slipping,DTC", "pro", 14.99, 134, 4.7, 18, True),

            ("diagnostics", "ABS/ESP Warning Diagnostic", "abs-esp-diagnostic",
             "Diagnostic workflow for ABS and electronic stability program warning lights.",
             "Systematic diagnosis of ABS/ESP warning indicators including sensor testing, module communication, and hydraulic system checks.",
             ["Document exact warning behavior and conditions", "Scan all modules for ABS/ESP related DTCs",
              "Check brake fluid level and condition", "Test individual wheel speed sensors with multimeter",
              "Inspect wheel speed sensor tone rings for damage", "Check ABS module wiring and connectors",
              "Test ABS hydraulic pump and valves", "Verify steering angle sensor calibration",
              "Perform road test with scanner live data", "Document findings and repair recommendation"],
             ["OBD-II scanner with ABS module access", "Digital multimeter",
              "Jack and jack stands", "Vehicle lifted and secured", "Wiring diagram for brake system"],
             "2 hr", "Advanced", "diagnostics,ABS,ESP,brake warning,sensors", "pro", 17.99, 98, 4.6, 14, False),

            ("diagnostics", "Battery/Charging System Test", "battery-charging-test",
             "Comprehensive battery health and alternator charging system evaluation.",
             "Full electrical system test covering battery condition, alternator output, parasitic draw, and starter circuit health.",
             ["Visual inspection of battery terminals and cables", "Test battery voltage with engine off",
              "Perform battery load test or conductance test", "Check alternator output voltage at idle",
              "Measure alternator amperage output under load", "Test for parasitic battery draw",
              "Inspect belt tension driving alternator", "Check starter circuit voltage drop",
              "Verify battery registration if required", "Document results and recommend replacement if needed"],
             ["Battery tester/load tester", "Digital multimeter with amp clamp",
              "Battery terminal cleaner", "Service information for battery specs",
              "Memory saver tool for retention"],
             "45 min", "Beginner", "diagnostics,battery,alternator,charging,electrical", "free", 0, 312, 4.8, 41, True),

            # --- Additional Maintenance ---
            ("maintenance", "Brake Fluid Flush", "brake-fluid-flush",
             "Complete brake fluid exchange service with system bleed.",
             "Full brake fluid flush using pressure or vacuum bleeding method to remove old contaminated fluid and replace with fresh DOT-rated fluid.",
             ["Verify correct brake fluid spec for vehicle", "Connect pressure bleeder or vacuum tool",
              "Open bleeder valves starting from furthest wheel", "Flush old fluid from each corner",
              "Monitor fluid clarity at each bleeder", "Refill master cylinder reservoir between wheels",
              "Verify no air in system with pedal feel test", "Check for leaks at all fittings",
              "Road test and confirm firm brake pedal", "Document fluid type and mileage for next service"],
             ["Brake fluid specified for vehicle", "Pressure bleeder or vacuum bleeder kit",
              "Catch containers for old fluid", "Box wrench set for bleeder valves",
              "Brake pedal feel is firm after bleeding"],
             "1 hr", "Intermediate", "maintenance,brakes,fluid flush,bleeding,DOT", "free", 0, 178, 4.5, 23, False),

            ("maintenance", "Power Steering Fluid Service", "power-steering-fluid-service",
             "Power steering fluid flush and system inspection.",
             "Complete power steering fluid exchange including reservoir, lines, and rack inspection for leaks and wear.",
             ["Identify correct power steering fluid type", "Raise front wheels off ground",
              "Siphon old fluid from reservoir", "Disconnect return line and drain rack",
              "Flush system with new fluid", "Reconnect lines and refill reservoir",
              "Turn wheel lock-to-lock to bleed air", "Check for leaks at all connections",
              "Inspect power steering pump for noise or wear", "Verify smooth operation and top off fluid"],
             ["Correct PS fluid for vehicle", "Turkey baster or fluid siphon",
              "Drain pan", "Jack and jack stands",
              "Funnel for clean filling"],
             "45 min", "Beginner", "maintenance,power steering,fluid,flush,rack", "free", 0, 145, 4.4, 17, False),

            ("maintenance", "Spark Plug Replacement", "spark-plug-replacement",
             "Spark plug replacement service with inspection and gap verification.",
             "Systematic spark plug change including removal inspection, gap check, and torque installation per manufacturer spec.",
             ["Gather correct spark plug part number and specs", "Remove ignition coils or spark plug wires",
              "Use compressed air to clean plug wells", "Remove old spark plugs one at a time",
              "Inspect old plugs for abnormal wear patterns", "Verify new plug gap matches spec",
              "Install new plugs hand-tight then torque to spec", "Reinstall coils or wires",
              "Start engine and verify smooth idle", "Document mileage and next replacement interval"],
             ["Correct spark plugs in stock", "Spark plug socket and extension",
              "Torque wrench", "Gap gauge",
              "Compressed air source"],
             "1 hr", "Beginner", "maintenance,spark plugs,ignition,tune-up", "pro", 9.99, 256, 4.6, 31, False),

            ("maintenance", "Cabin Air Filter & AC Service", "cabin-filter-ac-service",
             "Cabin air filter replacement with AC system performance check.",
             "Replace cabin air filter and perform AC system check including vent temperature, refrigerant level, and evaporator condition.",
             ["Locate cabin air filter access point", "Remove old cabin air filter and note condition",
              "Clean filter housing of debris", "Install new cabin air filter in correct orientation",
              "Start engine and activate AC to max cool", "Measure vent temperature with thermometer",
              "Check AC compressor engagement and clutch", "Inspect visible refrigerant lines for damage",
              "Verify blower motor operation all speeds", "Document findings and AC performance metrics"],
             ["Replacement cabin air filter", "AC thermometer probe",
              "Basic hand tools for filter access", "Refrigerant spec for vehicle",
              "UV dye kit for leak detection if needed"],
             "30 min", "Beginner", "maintenance,AC,cabin filter,air conditioning,ventilation", "free", 0, 203, 4.5, 26, True),

            # --- Additional Repair ---
            ("repair", "Rear Brake Job", "rear-brake-job",
             "Rear brake pad and rotor replacement service.",
             "Complete rear brake service including pad replacement, rotor resurfacing or replacement, caliper inspection, and hardware refresh.",
             ["Verify brake pad thickness and rotor condition", "Raise vehicle and remove rear wheels",
              "Remove caliper and hang with wire", "Remove old pads and hardware",
              "Compress caliper piston with tool", "Remove rotor and measure thickness",
              "Compare to minimum spec and decide resurface or replace", "Install new rotor or confirm resurfaced",
              "Install new hardware clips and pads", "Reinstall caliper and torque mounting bolts",
              "Reinstall wheels and torque lug nuts", "Pump brakes to seat pads and road test"],
             ["Rear brake pads in stock", "Rear rotors available if replacement needed",
              "Caliper piston compression tool", "Brake cleaner spray",
              "Torque wrench for lug nuts and caliper bolts"],
             "1.5 hr", "Intermediate", "repair,brakes,rear,pads,rotors,caliper", "pro", 12.99, 187, 4.7, 25, False),

            ("repair", "Wheel Bearing Replacement", "wheel-bearing-replacement",
             "Front or rear wheel bearing hub assembly replacement.",
             "Complete wheel bearing replacement procedure including hub removal, bearing press or hub assembly swap, and ABS sensor verification.",
             ["Verify bearing play and noise source", "Raise vehicle and remove wheel",
              "Disconnect ABS sensor if applicable", "Remove brake caliper and bracket",
              "Remove rotor to access hub", "Remove hub assembly or press out bearing",
              "Clean mounting surface thoroughly", "Install new bearing/hub assembly",
              "Torque axle nut to spec with new nut", "Reinstall brake components and wheel",
              "Verify ABS function after repair", "Road test and check for noise"],
             ["Replacement wheel bearing/hub assembly", "Bearing press or slide hammer",
              "Axle nut (use new one)", "Torque wrench",
              "Anti-seize compound"],
             "2 hr", "Advanced", "repair,wheel bearing,hub,ABS,noise", "enterprise", 24.99, 112, 4.6, 15, True),

            ("repair", "CV Axle Replacement", "cv-axle-replacement",
             "Constant velocity axle shaft replacement for front-wheel drive vehicles.",
             "Full CV axle replacement including boot inspection, joint evaluation, and proper installation with torque specs.",
             ["Identify damaged CV axle (boot tear, clicking noise)", "Raise vehicle and remove wheel",
              "Remove axle nut", "Disconnect lower ball joint or strut pinch bolt",
              "Push knuckle outward to separate axle", "Remove axle from transmission side",
              "Inspect transmission seal and output shaft", "Install new axle into transmission",
              "Reconnect suspension components", "Torque axle nut and suspension bolts to spec",
              "Reinstall wheel and road test", "Verify no vibration or noise"],
             ["Replacement CV axle", "Axle nut (new)", "Ball joint separator tool",
              "Transmission fluid for top-off", "Torque wrench"],
             "2.5 hr", "Advanced", "repair,CV axle,drivetrain,boot,FWD", "enterprise", 29.99, 89, 4.5, 12, False),

            ("repair", "Fuel Injector Cleaning", "fuel-injector-cleaning",
             "Professional fuel injector cleaning and fuel system service.",
             "Off-car or on-car fuel injector cleaning service including pressure test, flow rate verification, and intake valve cleaning.",
             ["Connect fuel pressure gauge and baseline pressure", "Disconnect fuel rail feed line",
              "Connect cleaning canister with solvent", "Start engine on cleaning solvent",
              "Monitor fuel pressure during cleaning", "Run until cleaning solution is consumed",
              "Reconnect normal fuel supply", "Check fuel pressure at idle and under load",
              "Inspect fuel rail and connections for leaks", "Document pressure readings and performance improvement"],
             ["Fuel injector cleaning kit", "Fuel pressure gauge",
              "Cleaning solvent solution", "Safety glasses and gloves",
              "Fire extinguisher nearby"],
             "1 hr", "Intermediate", "repair,fuel injector,cleaning,fuel system,performance", "pro", 11.99, 134, 4.4, 16, False),

            ("repair", "Radiator Replacement", "radiator-replacement",
             "Complete radiator replacement with coolant system flush.",
             "Full radiator replacement including coolant drain, system flush, new radiator installation, and thermostat verification.",
             ["Drain coolant from petcock into catch pan", "Remove upper and lower radiator hoses",
              "Disconnect transmission cooler lines if applicable", "Remove cooling fan assembly",
              "Remove mounting bolts and extract old radiator", "Compare old and new radiator dimensions",
              "Transfer any mounts or brackets to new radiator", "Install new radiator and secure mounting",
              "Reconnect all hoses, lines, and fan assembly", "Refill with correct coolant mixture",
              "Bleed air from cooling system", "Start engine and check for leaks at operating temp"],
             ["Replacement radiator", "Correct coolant/antifreeze", "Drain pan",
              "Hose clamps if replacing hoses", "Thermostat if replacing"],
             "3 hr", "Intermediate", "repair,radiator,cooling,coolant,overheating", "enterprise", 34.99, 98, 4.6, 13, True),

            # --- Additional Scrap ---
            ("scrap", "Scrap Price Lookup Workflow", "scrap-price-lookup",
             "Real-time scrap metal pricing research and quote generation workflow.",
             "Systematic process for researching current scrap metal prices, contacting yards, and generating competitive buy/sell quotes.",
             ["Identify material type and composition", "Weigh materials on calibrated scale",
              "Check current spot prices for metals", "Contact minimum 3 local scrap yards",
              "Request quotes based on weight and grade", "Compare pricing and factor in distance",
              "Calculate net value after transport costs", "Generate quote for customer",
              "Document pricing sources and date", "Set follow-up reminder for price updates"],
             ["Digital scale calibrated", "Internet access for price databases",
              "Contact list of local scrap yards", "Transport vehicle availability",
              "Pricing spreadsheet or tool"],
             "30 min", "Beginner", "scrap,pricing,lookup,metals,quote,market", "free", 0, 167, 4.3, 19, False),

            ("scrap", "Hazardous Material Handling", "hazardous-material-handling",
             "Safe handling and disposal workflow for hazardous automotive waste.",
             "Compliant procedure for handling e-waste, batteries, fluids, and other hazardous materials from vehicles and shop operations.",
             ["Identify hazardous material type and hazard class", "Don appropriate PPE for material",
              "Contain material in approved container", "Label container with content and date",
              "Segregate incompatible materials", "Store in designated hazmat area",
              "Schedule pickup with licensed hauler", "Complete manifest and chain-of-custody docs",
              "Verify disposal certificate received", "File records for regulatory compliance"],
             ["Approved hazmat containers", "PPE (gloves, goggles, suit)",
              "Hazmat labels and placards", "Licensed waste hauler contract",
              "Safety data sheets for all materials"],
             "1 hr", "Advanced", "scrap,hazardous,compliance,disposal,safety,EPA", "premium", 19.99, 56, 4.7, 8, False),

            ("scrap", "Scrap Yard Load Optimization", "scrap-load-optimization",
             "Workflow for maximizing scrap load value through sorting and preparation.",
             "Strategic sorting and preparation workflow to maximize revenue from scrap yard deliveries through proper material separation.",
             ["Catalog all available scrap materials", "Separate ferrous from non-ferrous metals",
              "Sort non-ferrous by type (copper, aluminum, brass, etc.)", "Strip insulation from copper wire",
              "Remove steel contaminants from aluminum", "Grade materials per yard specifications",
              "Check current prices by grade", "Calculate optimal load composition",
              "Weigh each sorted category", "Schedule delivery to highest-bidding yard"],
             ["Sorting bins or areas", "Wire stripping tool", "Magnet for ferrous identification",
              "Calibrated scale", "Yard grading reference sheet"],
             "45 min", "Intermediate", "scrap,optimization,sorting,grading,revenue", "free", 0, 112, 4.5, 14, False),

            # --- Additional Estimates ---
            ("estimates", "Used Car Dealer Inspection Package", "dealer-inspection-package",
             "Bulk pre-purchase inspection workflow for used car dealerships.",
             "Streamlined multi-vehicle inspection package designed for dealerships needing quick, consistent condition reports on trade-ins and auction purchases.",
             ["Receive vehicle batch from dealer contact", "Assign VIN and stock number in system",
              "Perform exterior condition assessment", "Check all fluids and mechanical components",
              "Scan all modules for DTCs", "Test electrical systems and accessories",
              "Perform road test", "Check tires and undercarriage",
              "Generate standardized condition report", "Submit report with repair priority ranking and cost estimate"],
             ["Bulk inspection checklist template", "Diagnostic scanner",
              "Digital camera for documentation", "Dealer contact and pricing agreement",
              "Batch processing work order template"],
             "1 hr", "Intermediate", "estimates,dealer,inspection,bulk,pre-purchase", "enterprise", 39.99, 78, 4.6, 10, True),

            ("estimates", "Fleet Maintenance Estimate", "fleet-maintenance-estimate",
             "Multi-vehicle maintenance estimate for fleet management contracts.",
             "Comprehensive estimate generation for fleet accounts covering multiple vehicles with contract-based pricing and volume discounts.",
             ["Pull fleet vehicle roster from CRM", "Identify vehicles due for scheduled maintenance",
              "Generate individual vehicle estimates", "Apply fleet contract discount tiers",
              "Consolidate into single master estimate", "Prioritize by vehicle criticality",
              "Identify parts that can be batch-ordered", "Schedule bay time allocation",
              "Submit estimate to fleet manager for approval", "Track approval status and schedule work"],
             ["Fleet contract terms on file", "Vehicle maintenance schedules defined",
              "Fleet discount pricing structure", "Parts supplier fleet pricing",
              "Bay scheduling calendar"],
             "1.5 hr", "Intermediate", "estimates,fleet,maintenance,contract,volume,discount", "pro", 24.99, 65, 4.5, 8, False),

            ("estimates", "Insurance Claim Estimate", "insurance-claim-estimate",
             "Insurance-specific repair estimate formatted for claims adjusters.",
             "Estimate formatted to insurance industry standards with OEM procedures, labor times, and parts pricing aligned to CCC, Mitchell, or Audatex formats.",
             ["Collect accident details and photos", "Document all visible damage systematically",
              "Reference OEM repair procedures", "Look up labor times in estimation database",
              "Price parts using insurance-rate parts suppliers", "Identify blend and refinish requirements",
              "Apply regional labor rate", "Format estimate per carrier requirements",
              "Include supplements for hidden damage protocol", "Submit estimate to adjuster with documentation"],
             ["Estimation software access (CCC/Mitchell)", "OEM repair procedure database",
              "Insurance carrier supplement guidelines", "Photos documented and organized",
              "Claim number and adjuster contact info"],
             "2 hr", "Advanced", "estimates,insurance,claim,adjuster,OEM,CCC", "premium", 29.99, 87, 4.7, 11, True),

            ("estimates", "Customer-Provided Parts Estimate", "customer-parts-estimate",
             "Labor-only estimate workflow when customer supplies their own parts.",
             "Generate a labor-only estimate with appropriate liability disclaimers for customers who purchase parts independently.",
             ["Review customer-provided parts for compatibility", "Document part numbers and condition",
              "Verify parts are correct for vehicle application", "Note warranty limitations with customer parts",
              "Calculate labor time per operation", "Apply shop labor rate to each operation",
              "Add shop supplies and environmental fees", "Generate estimate with disclaimer language",
              "Have customer sign parts liability waiver", "Schedule service upon approval"],
             ["Parts liability waiver form", "Parts compatibility reference",
              "Labor time guide (AllData/Mitchell)", "Customer parts inspection checklist",
              "Shop rate schedule"],
             "30 min", "Beginner", "estimates,labor only,customer parts,waiver,liability", "free", 0, 156, 4.3, 21, False),

            # --- Additional Compliance ---
            ("compliance", "Refrigerant Recovery Certification", "refrigerant-recovery-cert",
             "EPA 608 compliant refrigerant recovery and recycling procedure.",
             "Certified workflow for recovering vehicle refrigerant per EPA Section 608 regulations with proper documentation and equipment handling.",
             ["Verify technician EPA 608 certification is current", "Connect recovery machine to vehicle AC ports",
              "Record initial system pressure readings", "Begin refrigerant recovery process",
              "Monitor recovery machine until vacuum achieved", "Record recovered refrigerant amount",
              "Verify recovery machine calibration date", "Check for system leaks under vacuum",
              "Document refrigerant type and quantity", "File EPA compliance records"],
             ["EPA 608 certified technician", "Recovery/recycling machine calibrated",
              "Refrigerant identifier tool", "Recovery log sheets",
              "AC manifold gauge set"],
             "45 min", "Intermediate", "compliance,EPA,refrigerant,recovery,608,AC", "premium", 14.99, 45, 4.6, 7, False),

            ("compliance", "Waste Oil Disposal Procedure", "waste-oil-disposal",
             "Proper used oil handling, storage, and disposal compliance workflow.",
             "Complete workflow for collecting, storing, and disposing of used motor oil, hydraulic fluid, and other waste oils per EPA and state regulations.",
             ["Set up waste oil collection containers", "Label containers with content type and date",
              "Train staff on spill prevention procedures", "Collect oil from service bays regularly",
              "Maintain oil storage area per fire code", "Schedule pickup from licensed waste oil hauler",
              "Complete waste oil manifest documentation", "Verify hauler has proper permits",
              "File disposal records for 3 years", "Conduct annual storage area inspection"],
             ["Approved waste oil containers", "Secondary containment in place",
              "Licensed waste oil hauler contract", "Spill kit available",
              "Manifest documentation forms"],
             "1 hr", "Intermediate", "compliance,waste oil,disposal,EPA,storage,environment", "free", 0, 98, 4.4, 12, False),

            ("compliance", "Tool Calibration Schedule", "tool-calibration-schedule",
             "Scheduled calibration tracking for precision shop tools and equipment.",
             "Systematic workflow for tracking and performing calibration on torque wrenches, dial indicators, pressure gauges, and measuring instruments.",
             ["Inventory all calibrated tools in shop", "Record current calibration dates and intervals",
              "Identify tools approaching calibration due date", "Schedule calibration service or in-house check",
              "Remove tools from service during calibration", "Calibrate per manufacturer specification",
              "Update calibration sticker with new date", "Record calibration results and any adjustments",
              "Return tools to service and update tracking", "Generate monthly calibration compliance report"],
             ["Calibration tracking database or spreadsheet", "Calibration service provider contact",
              "Calibration stickers/labels", "Manufacturer calibration procedures",
              "Secure storage for tools awaiting calibration"],
             "30 min", "Beginner", "compliance,calibration,tools,torque wrench,quality,measurement", "pro", 9.99, 67, 4.5, 9, False),

            ("compliance", "Fire Prevention Audit", "fire-prevention-audit",
             "Fire safety inspection and prevention audit for auto repair facilities.",
             "Comprehensive fire prevention audit covering fire suppression systems, flammable storage, electrical safety, and emergency response preparedness.",
             ["Inspect fire extinguisher placement and expiry dates", "Check flammable storage cabinet condition",
              "Verify chemical storage per SDS requirements", "Inspect electrical panels and clearances",
              "Test emergency lighting and exit signs", "Review fire suppression system inspection tags",
              "Check ventilation and fume extraction systems", "Verify hot work permit procedures in place",
              "Review emergency evacuation plan and drills", "Document findings and corrective actions"],
             ["Fire safety inspection checklist", "Fire extinguisher inspection log",
              "Building fire suppression system records", "Emergency evacuation plan",
              "Hot work permit forms"],
             "2 hr", "Advanced", "compliance,fire safety,audit,prevention,OSHA,extinguisher", "enterprise", 22.99, 54, 4.7, 6, True),

            # --- Additional Service ---
            ("service", "New Customer Onboarding", "new-customer-onboarding",
             "Welcome workflow for new retail and commercial customers.",
             "Structured onboarding process to capture customer information, set up accounts, and establish communication preferences for long-term retention.",
             ["Greet customer and collect vehicle information", "Enter vehicle data into CRM system",
              "Capture customer contact preferences", "Review service history from previous shop if available",
              "Explain shop services and warranty policies", "Set up customer account with payment preferences",
              "Schedule first service appointment", "Send welcome email with shop info",
              "Assign customer to appropriate service tier", "Follow up within 48 hours after first visit"],
             ["CRM system ready", "New customer intake form", "Welcome packet prepared",
              "Shop brochures available", "First-time customer promotion defined"],
             "20 min", "Beginner", "service,onboarding,new customer,welcome,CRM,retention", "free", 0, 234, 4.8, 32, True),

            ("service", "VIP Customer Program", "vip-customer-program",
             "Loyalty tier management and VIP customer service workflow.",
             "Manage customer loyalty program including tier qualification, benefits tracking, and VIP service scheduling for high-value customers.",
             ["Review customer spending history in CRM", "Determine current loyalty tier qualification",
              "Notify customer of tier status and benefits", "Schedule VIP-only service appointments",
              "Apply loyalty discounts to invoices", "Track reward points and redemptions",
              "Provide priority scheduling for VIP customers", "Send birthday and anniversary offers",
              "Review program performance quarterly", "Adjust tier thresholds based on data"],
             ["Loyalty program rules defined", "CRM loyalty module configured",
              "VIP benefit schedule documented", "Marketing email templates ready",
              "Reporting dashboard for program metrics"],
             "30 min", "Intermediate", "service,VIP,loyalty,retention,program,tier", "pro", 14.99, 102, 4.6, 14, False),

            ("service", "Seasonal Promotion Campaign", "seasonal-promotion-campaign",
             "Marketing workflow for seasonal service promotions and campaigns.",
             "Plan and execute seasonal service campaigns including winter prep, summer AC, back-to-school, and holiday specials with tracking.",
             ["Identify upcoming seasonal service opportunity", "Define promotion offer and pricing",
              "Create marketing materials and messaging", "Set campaign start and end dates",
              "Configure CRM for campaign tracking", "Launch email and social media campaign",
              "Brief counter staff on promotion details", "Track appointment bookings per campaign",
              "Measure conversion rate and revenue impact", "Document results and plan next campaign"],
             ["Marketing email platform access", "Social media accounts configured",
              "Promotion pricing approved by management", "Campaign tracking codes set up",
              "Previous campaign performance data"],
             "1 hr", "Intermediate", "service,marketing,promotion,seasonal,campaign,email", "premium", 17.99, 78, 4.4, 11, False),

            ("service", "Referral Program Management", "referral-program-management",
             "Customer referral tracking and reward fulfillment workflow.",
             "Manage the complete referral program lifecycle from tracking referrals through reward delivery to both referrer and new customer.",
             ["Enroll customer in referral program", "Provide referral cards or unique referral code",
              "Track incoming referrals by source", "Verify new customer was referred by existing client",
              "Apply referral discount to new customer first visit", "Issue reward to referring customer",
              "Log referral outcome in CRM", "Send thank-you communication to referrer",
              "Analyze referral program ROI monthly", "Adjust reward structure based on performance"],
             ["Referral tracking system in CRM", "Referral cards or digital codes",
              "Reward options defined (discount, credit, gift card)", "Communication templates ready",
              "Referral program terms and conditions"],
             "15 min", "Beginner", "service,referral,marketing,loyalty,rewards,acquisition", "pro", 7.99, 143, 4.5, 18, False),

            # --- Additional Fleet ---
            ("fleet", "Fleet Onboarding Process", "fleet-onboarding",
             "New fleet account setup and integration workflow.",
             "Complete onboarding process for new fleet accounts including contract setup, vehicle roster, service agreements, and billing configuration.",
             ["Receive fleet account application", "Verify business credentials and insurance",
              "Negotiate service contract terms", "Set up billing account and payment terms",
              "Collect complete vehicle roster with VINs", "Assign fleet account manager",
              "Configure fleet-specific pricing in system", "Schedule initial vehicle inspections",
              "Provide fleet manager with portal access", "Conduct kickoff meeting with fleet contact"],
             ["Fleet application form", "Contract template ready",
              "Fleet pricing structure defined", "Portal account credentials",
              "Initial inspection scheduling slots available"],
             "3 hr", "Intermediate", "fleet,onboarding,account setup,contract,commercial", "enterprise", 34.99, 45, 4.7, 6, False),

            ("fleet", "Annual Fleet Audit", "fleet-annual-audit",
             "Comprehensive yearly review of fleet maintenance records and compliance.",
             "Annual audit of fleet vehicle maintenance history, compliance status, cost analysis, and performance metrics for fleet management reporting.",
             ["Pull complete fleet maintenance records for year", "Review each vehicle's service history",
              "Verify DOT and safety inspection compliance", "Analyze maintenance cost per vehicle",
              "Identify vehicles approaching replacement threshold", "Review parts and labor cost trends",
              "Compare actual vs scheduled maintenance adherence", "Generate fleet health scorecard",
              "Present audit findings to fleet manager", "Develop recommendations for next year"],
             ["Fleet maintenance database", "Cost tracking reports",
              "DOT compliance checklist", "Vehicle lifecycle cost model",
              "Audit report template"],
             "4 hr", "Advanced", "fleet,audit,annual,compliance,cost analysis,report", "enterprise", 44.99, 38, 4.8, 5, True),

            ("fleet", "Emergency Roadside Assistance", "emergency-roadside-assistance",
             "Breakdown response and emergency service dispatch workflow.",
             "Rapid response workflow for fleet vehicle breakdowns including dispatch, on-site assessment, temporary repair, and towing coordination.",
             ["Receive emergency breakdown call", "Log vehicle location and symptoms",
              "Dispatch mobile service unit or tow truck", "Communicate ETA to driver and fleet manager",
              "Perform on-site assessment of vehicle", "Determine if repair is possible on-site",
              "Arrange towing if repair not feasible", "Provide driver with alternative transportation info",
              "Complete emergency service documentation", "Schedule follow-up repair at shop if needed"],
             ["Emergency dispatch contact list", "Towing service contract with SLA",
              "Mobile service unit equipped and ready", "Driver communication protocol",
              "Emergency parts inventory on truck"],
             "15 min", "Beginner", "fleet,emergency,roadside,breakdown,dispatch,towing", "premium", 19.99, 91, 4.8, 16, False),
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
        logger.info("Template data seeded: 3 plans, 8 categories, 57 templates")

    except Exception as e:
        db.rollback()
        logger.exception("Failed to seed template data")
    finally:
        db.close()
