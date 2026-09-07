"""
Marketplace Domain Knowledge Base for ATV & Buggy Platform.
Defines the business logic, operational constraints, pricing rules, and logistics.
"""

MARKETPLACE_KNOWLEDGE_PROMPT = """
KEY PLATFORM & BOOKING KNOWLEDGE:
1. Marketplace Overview:
   - atvandbuggy.com is an adventure marketplace connecting guests with independent, certified desert tour operators.
   - Each vendor operates dedicated fleets, custom desert staging camps, independent VAT rates, and local service fees.

2. Vehicles & Capacities:
   - 1-Seater: Quad Bikes / ATVs
   - 2-Seater: Dune Buggies
   - 4-Seater: Family UTVs
   - Available Tour Durations: 30 minutes, 60 minutes, 120 minutes (2 hours), and 180 minutes (3 hours).
   - Exact Plate Reservation: Guests book specific physical vehicles by plate number to ensure guaranteed availability without double-booking.

3. Transportation Options to the Desert Camp:
   - Option 1: Self-Drive (Free / $0). We provide direct GPS coordinates to the operator's desert staging camp.
   - Option 2: Group Pickup. Scheduled departure shifts, charged at a fixed per-person rate. Mandatory contact phone required.
   - Option 3: Private Pickup (VIP Driver / Limousine). Door-to-door transfer with dynamic pricing based on distance in kilometers to the desert camp, vehicle type, and passenger count.

4. Pricing and VAT Calculation:
   - Final Total = Taxable Subtotal + VAT.
   - Taxable Subtotal = (Vehicle Rental Price - Promo Discount) + Transportation Fee + Service Fee.
   - VAT is calculated as a percentage of the Taxable Subtotal according to local regulations.

5. Promo Codes & Discounts:
   - Promo codes are valid for first-time purchases only and are strictly single-use per customer.

6. Advance Booking Lead-Time:
   - Each tour operator requires a minimum advance booking buffer (lead time) before tour departure to prepare the vehicles and assign desert guides. Last-minute bookings within this buffer window cannot be accepted.

7. Confirmation & Camp Check-In:
   - Guest Checkout: Customers can checkout quickly as a guest or create an account to view past trips.
   - Digital QR Tickets: After payment, customers instantly receive a confirmation with a unique digital QR ticket for each reserved vehicle.
   - On-Site Check-In: Upon arriving at the desert camp, staff scan the QR code to check in the party and hand over the vehicles.
"""
