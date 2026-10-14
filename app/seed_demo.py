"""Demo seed: fake customers, vehicles, work orders, invoices and activity."""
import random
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import (
    Customer, Vehicle, WorkOrder, WorkOrderItem, Part,
    Technician, Invoice, ScrapPickup, ScrapInventory, ScrapVendor,
    PurchaseOrder, PurchaseOrderItem, Lead, Alert,
)
from app.seed_data import (
    FIRST_NAMES, LAST_NAMES, STREETS, CITIES, METALS, SPECIALTIES,
    VEHICLE_DATA, LEAD_SOURCES, LEAD_STATUSES,
)

logger = logging.getLogger(__name__)


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
                name=f"{fn} {ln}",
                email=f"{fn.lower()}.{ln.lower()}@email.com",
                phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                address=f"{random.randint(100,9999)} {random.choice(STREETS)}, {random.choice(CITIES)}, TX",
                notes=f"Customer since {random.randint(2020,2025)}",
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
                engine_type=random.choice(["Gasoline","Diesel","Hybrid","Electric"]),
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
                name=name, specialization=random.choice(SPECIALTIES),
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
                category=cat, cost_price=cost, selling_price=round(cost * random.uniform(1.4,2.2),2),
                quantity_on_hand=qty, min_quantity=max(3, qty // 4),
                supplier=f"AutoZone" if random.random()>0.5 else "O'Reilly",
                created_at=datetime.now() - timedelta(days=random.randint(1,180))
            )
            db.add(p)
            parts.append(p)
        db.flush()

        # Work Orders
        statuses = ["New","In Progress","Completed","Waiting Parts"]
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
            status = random.choice(statuses)
            wo = WorkOrder(
                customer_id=c.id, vehicle_id=v.id,
                title=random.choice(wo_descs),
                description=random.choice(wo_descs),
                status=status,
                labor_hours=round(random.uniform(0.5,8),1),
                labor_rate=85,
                odometer=random.randint(10000,150000),
                created_at=datetime.now() - timedelta(days=random.randint(0,90)),
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
                    unit_price=part.selling_price,
                    total_price=round(qty * part.selling_price, 2),
                    is_labor=False,
                )
                db.add(wop)
                part.quantity_on_hand = max(0, part.quantity_on_hand - qty)
        db.flush()

        # Invoices
        for wo in [w for w in work_orders if w.status == "Completed"][:20]:
            inv_items = db.query(WorkOrderItem).filter(WorkOrderItem.work_order_id == wo.id).all()
            items_total = float(sum(ip.quantity * ip.unit_price for ip in inv_items))
            labor = float(wo.labor_hours or 0) * 85
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
