"""
ecommerce_data.py
Synthetic e-commerce event generator.

Event types:
  - PRODUCT_VIEW   : user browsed a product page
  - ADD_TO_CART    : user added product to cart
  - ORDER_PLACED   : user completed a purchase
  - SEARCH         : user searched for a keyword
  - RETURN         : user returned an ordered item

Each event is a dict:
  { type, user_id, product_id, category, price, timestamp }
"""
import random
import time

# ── Catalogue ─────────────────────────────────────────────────────────────
# 12 categories x ~50 products each = ~580 total products
# This gives CM Sketch enough distinct items to show real 1-5% errors
CATEGORIES = {
    "Electronics": [
        "Laptop Pro", "Laptop Air", "Gaming Laptop", "Ultrabook", "Chromebook",
        "Smartphone X", "Smartphone Pro", "Budget Phone", "Flagship Phone", "Foldable Phone",
        "Wireless Headphones", "Noise-Cancelling Headphones", "Gaming Headset", "Earbuds", "Over-Ear Headphones",
        "Tablet 10in", "Tablet 12in", "Drawing Tablet", "Kids Tablet", "E-Reader",
        "Smartwatch Series 1", "Smartwatch Series 2", "Fitness Band", "GPS Watch", "Kids Smartwatch",
        "DSLR Camera", "Mirrorless Camera", "Action Camera", "Instant Camera", "Webcam",
        "Bluetooth Speaker", "Smart Speaker", "Portable Speaker", "Soundbar", "Home Theatre",
        "4K Monitor", "Gaming Monitor", "Ultrawide Monitor", "Portable Monitor", "Curved Monitor",
        "Mechanical Keyboard", "Wireless Keyboard", "Gaming Mouse", "Trackpad", "USB Hub",
        "WiFi Router", "Mesh Router", "Network Switch", "External SSD", "Portable HDD",
    ],
    "Fashion": [
        "Running Sneakers", "Casual Sneakers", "High-Top Sneakers", "Slip-On Shoes", "Loafers",
        "Leather Jacket", "Denim Jacket", "Bomber Jacket", "Puffer Jacket", "Raincoat",
        "Slim Jeans", "Straight Jeans", "Jogger Pants", "Chinos", "Cargo Pants",
        "Graphic T-Shirt", "Plain T-Shirt", "Polo Shirt", "Formal Shirt", "Linen Shirt",
        "Floral Dress", "Midi Dress", "Maxi Dress", "Wrap Dress", "Party Dress",
        "Tote Bag", "Leather Handbag", "Clutch Bag", "Backpack Purse", "Crossbody Bag",
        "Aviator Sunglasses", "Wayfarer Sunglasses", "Round Sunglasses", "Sports Sunglasses", "Blue Light Glasses",
        "Analog Watch", "Digital Watch", "Smartband", "Luxury Watch", "Sports Watch",
        "Wool Sweater", "Hoodie", "Cardigan", "Turtleneck", "Sweatshirt",
        "Leather Belt", "Canvas Belt", "Silk Scarf", "Beanie Hat", "Gloves",
    ],
    "Home & Kitchen": [
        "3-Seater Sofa", "Sectional Sofa", "Recliner Chair", "Bean Bag", "Futon",
        "Floor Lamp", "Table Lamp", "Pendant Light", "LED Strip", "Smart Bulb",
        "Hand Blender", "Countertop Blender", "Food Processor", "Stand Mixer", "Juicer",
        "Drip Coffee Maker", "Espresso Machine", "French Press", "Cold Brew Maker", "Electric Kettle",
        "Robot Vacuum", "Stick Vacuum", "Handheld Vacuum", "Steam Mop", "Air Purifier",
        "Memory Foam Mattress", "Spring Mattress", "Latex Mattress", "Mattress Topper", "Pillow Set",
        "Blackout Curtains", "Sheer Curtains", "Roman Blinds", "Roller Shades", "Bamboo Blinds",
        "Non-Stick Pan", "Cast Iron Skillet", "Stainless Pot", "Wok", "Dutch Oven",
        "Dining Table", "Bar Stool", "Office Chair", "Bookshelf", "TV Stand",
        "Aroma Diffuser", "Scented Candle", "Wall Clock", "Photo Frame", "Decorative Vase",
    ],
    "Books": [
        "Mystery Thriller", "Romance Novel", "Fantasy Epic", "Sci-Fi Classic", "Historical Fiction",
        "Self-Help Productivity", "Self-Help Mindset", "Self-Help Finance", "Self-Help Leadership", "Self-Help Habits",
        "Vegetarian Cookbook", "Baking Cookbook", "BBQ Cookbook", "Quick Meals Cookbook", "World Cuisine Cookbook",
        "Tech Biography", "Sports Biography", "Political Memoir", "Celebrity Memoir", "Artist Biography",
        "Data Science Textbook", "ML Textbook", "Cloud Computing Guide", "Algorithms Textbook", "OS Concepts",
        "Superhero Comic", "Manga Vol 1", "Graphic Novel", "Comic Anthology", "Webcomic Collection",
        "Children Picture Book", "Young Adult Novel", "Middle Grade Adventure", "Board Book", "Pop-up Book",
        "Business Strategy", "Marketing Guide", "Startup Playbook", "Economics 101", "Investing Basics",
        "Travel Guide India", "Travel Guide Europe", "Travel Guide Japan", "Photography Book", "Art History",
        "Poetry Collection", "Short Stories", "Drama Script", "Essays Collection", "Literary Classic",
    ],
    "Sports & Fitness": [
        "Yoga Mat 4mm", "Yoga Mat 6mm", "Yoga Block", "Yoga Strap", "Yoga Wheel",
        "Dumbbell 5kg", "Dumbbell 10kg", "Adjustable Dumbbell", "Barbell Set", "Kettlebell",
        "Road Running Shoes", "Trail Running Shoes", "Track Spikes", "Walking Shoes", "Cross Trainers",
        "Road Cycling Helmet", "MTB Helmet", "Cycling Gloves", "Cycling Jersey", "Padded Shorts",
        "Whey Protein", "Plant Protein", "BCAA Supplement", "Creatine", "Pre-Workout",
        "Tennis Racket Pro", "Tennis Racket Beginner", "Badminton Racket", "Table Tennis Set", "Squash Racket",
        "Football", "Basketball", "Volleyball", "Rugby Ball", "Cricket Ball",
        "Resistance Bands Set", "Pull-Up Bar", "Ab Roller", "Jump Rope", "Push-Up Handles",
        "Gym Bag", "Water Bottle", "Gym Gloves", "Weightlifting Belt", "Foam Roller",
        "Treadmill", "Exercise Bike", "Rowing Machine", "Elliptical", "Multi-Gym Station",
    ],
    "Beauty & Personal Care": [
        "Face Moisturizer", "Night Cream", "Eye Cream", "Sunscreen SPF50", "BB Cream",
        "Vitamin C Serum", "Retinol Serum", "Hyaluronic Serum", "Niacinamide Serum", "AHA BHA Serum",
        "Lipstick Matte", "Lipstick Glossy", "Lip Liner", "Lip Balm", "Lip Plumper",
        "Mascara", "Eyeliner Pencil", "Liquid Eyeliner", "Eyeshadow Palette", "Eyebrow Pencil",
        "Foundation Liquid", "Foundation Powder", "Concealer", "Setting Powder", "Setting Spray",
        "Shampoo Anti-Dandruff", "Shampoo Moisturising", "Conditioner", "Hair Mask", "Dry Shampoo",
        "Hair Straightener", "Curling Wand", "Hair Dryer", "Hair Oil", "Hair Serum",
        "Electric Toothbrush", "Whitening Toothpaste", "Mouthwash", "Dental Floss", "Tongue Scraper",
        "Body Lotion", "Body Scrub", "Body Oil", "Shower Gel", "Deodorant Roll-On",
        "Perfume Floral", "Perfume Woody", "Cologne Fresh", "Body Mist", "Room Spray",
    ],
    "Toys & Games": [
        "LEGO City Set", "LEGO Technic", "LEGO Star Wars", "LEGO Friends", "LEGO Creator",
        "Action Figure Hero", "Action Figure Villain", "Doll Classic", "Doll Fashion", "Doll House",
        "RC Car Buggy", "RC Drone Beginner", "RC Helicopter", "RC Boat", "RC Tank",
        "Board Game Strategy", "Board Game Family", "Card Game", "Dice Game", "Party Game",
        "Chess Set", "Checkers Set", "Scrabble", "Monopoly", "Cluedo",
        "Puzzle 500pc", "Puzzle 1000pc", "Puzzle 3D", "Puzzle Wooden", "Jigsaw Floor Puzzle",
        "Sketch Pad", "Watercolour Set", "Acrylic Paint Set", "Colouring Book", "Craft Kit",
        "Science Kit Chemistry", "Science Kit Robotics", "Science Kit Volcano", "Telescope Kids", "Microscope Kids",
        "Soft Toy Bear", "Soft Toy Elephant", "Plush Dinosaur", "Puppet Set", "Stress Ball",
        "Swing Set", "Slide", "Trampoline Small", "Sandpit", "Balance Bike",
    ],
    "Automotive": [
        "Dash Cam 1080p", "Dash Cam 4K", "Rear Camera", "360 Dash Cam", "Mirror Dash Cam",
        "Car Phone Mount Vent", "Car Phone Mount Dashboard", "Wireless Car Charger", "Car USB Charger", "Car Inverter",
        "Tyre Inflator Portable", "Jump Starter Pack", "Car Battery Charger", "OBD2 Scanner", "Multimeter Auto",
        "Seat Cover Leather", "Seat Cover Fabric", "Steering Wheel Cover", "Car Floor Mats", "Boot Liner",
        "Car Vacuum Mini", "Car Air Freshener", "Windscreen Sun Shade", "Car First Aid Kit", "Emergency Kit",
        "Engine Oil 5W30", "Engine Oil 10W40", "Coolant", "Brake Fluid", "Windscreen Washer",
        "Roof Rack", "Bike Carrier", "Tow Bar", "Bull Bar", "Nudge Bar",
        "LED Headlights", "Fog Lights", "Interior LED Strip", "Reverse Sensors", "Parking Camera",
    ],
    "Groceries & Gourmet": [
        "Organic Basmati Rice 5kg", "Brown Rice 2kg", "Quinoa 1kg", "Rolled Oats 1kg", "Muesli 500g",
        "Extra Virgin Olive Oil", "Coconut Oil", "Avocado Oil", "Sesame Oil", "Mustard Oil",
        "Dark Chocolate 70%", "Milk Chocolate Bar", "White Chocolate", "Chocolate Gift Box", "Protein Chocolate",
        "Green Tea 50 bags", "Black Tea 100 bags", "Chamomile Tea", "Matcha Powder", "Herbal Infusion",
        "Almonds 500g", "Cashews 500g", "Walnuts 250g", "Mixed Nuts", "Trail Mix",
        "Raw Honey 500g", "Manuka Honey", "Maple Syrup", "Agave Syrup", "Stevia Drops",
        "Wholewheat Pasta", "Rice Pasta", "Lentil Pasta", "Soba Noodles", "Rice Noodles",
        "Protein Granola", "Chia Seeds", "Flaxseeds", "Hemp Seeds", "Pumpkin Seeds",
        "Hot Sauce", "Soy Sauce", "Balsamic Vinegar", "Apple Cider Vinegar", "Worcestershire Sauce",
        "Sparkling Water 12pk", "Kombucha 6pk", "Coconut Water 6pk", "Almond Milk 1L", "Oat Milk 1L",
    ],
    "Health & Wellness": [
        "Multivitamin Men", "Multivitamin Women", "Vitamin D3", "Vitamin C 1000mg", "Vitamin B12",
        "Omega 3 Fish Oil", "Flaxseed Oil Caps", "Evening Primrose Oil", "Cod Liver Oil", "Krill Oil",
        "Probiotics 50bn", "Digestive Enzymes", "Collagen Powder", "Biotin 10000mcg", "Magnesium Glycinate",
        "Zinc Immune Support", "Elderberry Syrup", "Echinacea Extract", "Turmeric Curcumin", "Ashwagandha",
        "Blood Pressure Monitor", "Pulse Oximeter", "Digital Thermometer", "Glucometer Kit", "Body Weighing Scale",
        "Heating Pad", "Ice Pack Gel", "Tens Machine", "Knee Support Brace", "Back Support Belt",
        "Face Mask N95 10pk", "Surgical Masks 50pk", "Hand Sanitiser 500ml", "Disinfectant Spray", "First Aid Kit",
        "Meditation Cushion", "Acupressure Mat", "Sleep Eye Mask", "White Noise Machine", "Aromatherapy Kit",
        "Resistance Band Light", "Balance Board", "Posture Corrector", "Foot Massager", "Neck Massager",
        "Melatonin 5mg", "Sleep Aid Tea", "Magnesium Night Formula", "Lavender Pillow Spray", "CBD Oil Drops",
    ],
    "Baby & Kids": [
        "Baby Monitor Video", "Baby Monitor Audio", "Smart Baby Monitor", "Breathing Monitor", "Temperature Monitor",
        "Pram Travel System", "Lightweight Stroller", "Jogging Stroller", "Umbrella Stroller", "Baby Carrier Wrap",
        "Baby Cot Wooden", "Co-Sleeper Crib", "Travel Cot", "Moses Basket", "Baby Hammock",
        "Car Seat Group 0", "Car Seat Group 1", "Car Seat Group 2", "Booster Seat", "Isofix Base",
        "Highchair Classic", "Highchair Portable", "Booster Feeding Chair", "Footrest Cushion", "Seat Cushion",
        "Baby Bath Tub", "Baby Shampoo", "Baby Lotion", "Nappy Rash Cream", "Baby Wipes 80pk",
        "Feeding Bottle Glass", "Feeding Bottle Plastic", "Breast Pump Electric", "Breast Pump Manual", "Milk Storage Bags",
        "Baby Food Puree Set", "Toddler Snack Packs", "Organic Baby Cereal", "Teething Biscuits", "Fruit Pouches",
        "Nappies Size 1", "Nappies Size 2", "Nappies Size 3", "Training Pants", "Swim Nappies",
        "Baby Grow Set", "Sleepsuit 3pk", "Baby Hat Set", "Baby Socks Set", "Mittens Set",
    ],
    "Office & Stationery": [
        "A4 Printer Paper 500sh", "A3 Paper 250sh", "Cardstock 250gsm", "Tracing Paper Pad", "Graph Paper Pad",
        "Ballpoint Pens 10pk", "Gel Pens 12pk", "Fountain Pen", "Rollerball Pen", "Stylus Pen",
        "Stapler Heavy Duty", "Staples 5000pk", "Hole Punch 4-Ring", "Paper Clips 100pk", "Binder Clips Assorted",
        "Sticky Notes Yellow", "Sticky Notes Multicolour", "Page Flags Set", "Index Cards 200pk", "Post-It Super Sticky",
        "A4 Ring Binder", "Lever Arch File", "Document Wallet", "Expanding File Folder", "Magazine File Box",
        "Whiteboard 60x90", "Whiteboard 90x120", "Corkboard Notice Board", "Flip Chart Easel", "Monthly Planner Board",
        "Desk Organiser Tray", "Pen Holder Bamboo", "Monitor Riser Stand", "Laptop Stand Adjustable", "Document Holder",
        "Laminator A4", "Laminating Pouches 100pk", "Shredder P4 Level", "Binding Machine Comb", "Label Maker",
        "Highlighters 6pk Assorted", "Permanent Markers 4pk", "Whiteboard Markers 8pk", "Paint Markers", "Chalk Markers",
        "Scientific Calculator", "Printing Calculator", "30cm Ruler", "Set Square 45deg", "Compass Geometry Set",
    ],
}

# ── Build flat product list ───────────────────────────────────────────────
# Each entry: (product_id, name, category, price)
PRODUCTS = []
for cat, items in CATEGORIES.items():
    prefix = cat[:3].upper()
    for i, item in enumerate(items, 1):
        price = round(random.uniform(20, 1500), 2)
        PRODUCTS.append((f"{prefix}-{i:03d}", item, cat, price))

NUM_PRODUCTS = len(PRODUCTS)
NUM_USERS    = 500
USERS        = [f"USR-{str(i).zfill(4)}" for i in range(NUM_USERS)]

print(f"[ecommerce_data] Loaded {NUM_PRODUCTS} products across {len(CATEGORIES)} categories")

EVENT_TYPES = [
    "PRODUCT_VIEW", "PRODUCT_VIEW", "PRODUCT_VIEW",   # 3x weight — most common action
    "ADD_TO_CART",
    "ORDER_PLACED",
    "SEARCH",
    "RETURN",
]

# Popularity weights: Zipf-like — first products are "trending"
PRODUCT_WEIGHTS = [1 / (i + 1) ** 1.2 for i in range(NUM_PRODUCTS)]
_total = sum(PRODUCT_WEIGHTS)
PRODUCT_WEIGHTS = [w / _total for w in PRODUCT_WEIGHTS]


def generate_event(spike=False):
    """Generate a single random e-commerce event with timestamp."""
    event_type                             = random.choices(EVENT_TYPES)[0]
    user_id                                = random.choice(USERS)
    product_id, product_name, category, price = random.choices(
        PRODUCTS, weights=PRODUCT_WEIGHTS
    )[0]

    # During a spike (flash sale), bias toward views and orders
    if spike and random.random() < 0.6:
        event_type = random.choice(["PRODUCT_VIEW", "ORDER_PLACED", "ADD_TO_CART"])

    return {
        "type":         event_type,
        "user_id":      user_id,
        "product_id":   product_id,
        "product_name": product_name,
        "category":     category,
        "price":        float(price),
        "timestamp":    int(time.time()),
    }


def event_key(event, mode="product"):
    """Return a hashable key for an event, used in prob structures."""
    if mode == "product":
        return event["product_id"]
    elif mode == "user":
        return event["user_id"]
    elif mode == "category":
        return event["category"]
    elif mode == "user_product":
        return f"{event['user_id']}::{event['product_id']}"
    return event["product_id"]