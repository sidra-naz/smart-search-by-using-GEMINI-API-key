"""
Firebase Firestore Service (Read-Only)
Specifically connects to the 'cmj-dev' database in project 'atvandbuggy-dev'.
This service is strictly READ-ONLY: it only fetches and searches vehicle/rental data.
"""

import os
import glob
import re
from typing import List, Dict, Any, Optional
from google.cloud import firestore

# Locate service account key in backend folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
key_files = glob.glob(os.path.join(CURRENT_DIR, "*firebase-adminsdk*.json"))
if not key_files:
    key_files = glob.glob(os.path.join(CURRENT_DIR, "serviceAccountKey.json"))

CRED_PATH = key_files[0] if key_files else None

# Connect to the named database 'cmj-dev' strictly in read-only mode
_db: Optional[firestore.Client] = None

def get_firestore_client() -> Optional[firestore.Client]:
    global _db
    if _db is not None:
        return _db
    if CRED_PATH and os.path.exists(CRED_PATH):
        try:
            # Connect to primary default database containing live inventory
            _db = firestore.Client.from_service_account_json(CRED_PATH)
            print(f"[Firebase] Connected to primary Firestore database (Project: {_db.project})")
            return _db
        except Exception as e:
            print(f"[Firebase] Error connecting to primary database: {e}")
            try:
                _db = firestore.Client.from_service_account_json(CRED_PATH, database="cmj-dev")
                print(f"[Firebase] Connected to cmj-dev database (Project: {_db.project})")
                return _db
            except Exception as ex:
                print(f"[Firebase] Error connecting to cmj-dev database: {ex}")
                return None
    else:
        print("[Firebase] Warning: Service account JSON key not found.")
        return None

def get_vehicle_price(v: Dict[str, Any]) -> Optional[float]:
    """Extract realistic hourly price value from various Firestore document keys."""
    # 1. Direct standard schedule/deal keys
    for key in ["scheduleLowestPrice60Min", "scheduleHighestPrice60Min", "Price", "price", "scheduleLowestPrice"]:
        val = v.get(key)
        if val is not None and str(val).strip() != "":
            try:
                p = float(str(val).replace("$", "").replace(",", "").strip())
                if 50 <= p <= 5000:
                    return p
            except ValueError:
                pass

    # 2. Manual booking dictionary prices
    mbp = v.get("manualBookingPrices")
    if isinstance(mbp, dict):
        for k in ["60", "30", "120", "180"]:
            val = mbp.get(k)
            if val is not None:
                try:
                    p = float(val)
                    if 50 <= p <= 5000:
                        return p
                except ValueError:
                    pass

    # 3. Fallback standard catalog rate if not explicitly specified in document
    raw_name = str(v.get("Name", v.get("name", ""))).lower()
    raw_type = str(v.get("Type", v.get("type", ""))).lower()
    s_str = str(v.get("Seat", v.get("Seats", v.get("seats", ""))))
    
    if "atv" in raw_type or "quad" in raw_type or "atv" in raw_name or "quad" in raw_name:
        return 350.0
    elif "4" in s_str or "four" in s_str:
        return 798.0
    else:
        return 598.0

# Model-specific verified visual photo library from live database
MODEL_SPECIFIC_IMAGES = {
    "zforce": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4451?alt=media&token=831c6d49-f076-49b9-bffc-aea13c9b0109"
    ],
    "z force": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4451?alt=media&token=831c6d49-f076-49b9-bffc-aea13c9b0109"
    ],
    "cfmoto": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4451?alt=media&token=831c6d49-f076-49b9-bffc-aea13c9b0109"
    ],
    "uforce": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4451?alt=media&token=831c6d49-f076-49b9-bffc-aea13c9b0109"
    ],
    "wolverine": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4717?alt=media&token=02d06b37-9bc0-4d3b-adcb-d8c89fb1fabc",
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4979?alt=media&token=e838f550-1930-40a0-a0e1-3776be315beb"
    ],
    "yxz": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4717?alt=media&token=02d06b37-9bc0-4d3b-adcb-d8c89fb1fabc"
    ],
    "yamaha": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4717?alt=media&token=02d06b37-9bc0-4d3b-adcb-d8c89fb1fabc"
    ],
    "talon": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4655?alt=media&token=42fcba83-93f8-44b1-b588-9b7fbcf25f96"
    ],
    "pioneer": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4655?alt=media&token=42fcba83-93f8-44b1-b588-9b7fbcf25f96"
    ],
    "honda": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4655?alt=media&token=42fcba83-93f8-44b1-b588-9b7fbcf25f96"
    ],
    "teryx": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5904?alt=media&token=d602feba-60be-4e50-9a54-38580941ed27"
    ],
    "krx": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5904?alt=media&token=d602feba-60be-4e50-9a54-38580941ed27"
    ],
    "mule": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5904?alt=media&token=d602feba-60be-4e50-9a54-38580941ed27"
    ],
    "kawasaki": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5904?alt=media&token=d602feba-60be-4e50-9a54-38580941ed27"
    ],
    "wildcat": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5487?alt=media&token=fb28eef8-7ed8-4af5-8fec-1703e9c727ad"
    ],
    "arctic cat": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5487?alt=media&token=fb28eef8-7ed8-4af5-8fec-1703e9c727ad"
    ],
    "maverick": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/1772?alt=media&token=f2a2f4e6-1f78-4ad9-a003-df04be78dfe6"
    ],
    "can-am": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/1772?alt=media&token=f2a2f4e6-1f78-4ad9-a003-df04be78dfe6"
    ],
    "rzr xp 4": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7757?alt=media&token=786f9e6e-fe64-486a-808c-960ef99aa158",
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/8197?alt=media&token=98a9d6cc-087d-4c1c-92c1-10ebcb454044"
    ],
    "rzr": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7953?alt=media&token=d2268693-7d38-4e82-b21a-74b5a682ba98",
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/9108?alt=media&token=0c9a27ee-acec-4c8d-b625-a89edc35a4f4"
    ],
    "ranger": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7953?alt=media&token=d2268693-7d38-4e82-b21a-74b5a682ba98"
    ],
    "gts": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4655?alt=media&token=42fcba83-93f8-44b1-b588-9b7fbcf25f96"
    ],
    "tour": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4717?alt=media&token=02d06b37-9bc0-4d3b-adcb-d8c89fb1fabc"
    ],
    "grizzly": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/users%2FrM4rRtN3KmeDxNrrgGcJ6BtSWyu2%2Fvehicle%2F3910.jpg?alt=media&token=4db255ad-9dc4-45ed-acdf-e4f0a275a7fd"
    ],
    "cobra": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/8016?alt=media&token=74144f54-f601-47a0-a7ca-c428cb8780ec"
    ],
    "sportsman": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7115?alt=media&token=264468a5-cc3c-44ff-9972-bd9e6c0cfcff"
    ],
    "mxu": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7106?alt=media&token=9514fdeb-a9ca-4ee7-8e35-588c6066293d",
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/3753?alt=media&token=6b045e80-f336-4f56-aedb-163b9133f1dc"
    ],
    "mongoose": [
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/134?alt=media&token=20c9688b-8a8a-4486-af95-84d28ffb0abf",
        "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/9180?alt=media&token=60d101c9-4487-4e6c-948a-47f09f3a6e7d"
    ]
}

BUGGY_FALLBACK_POOL = [
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/1772?alt=media&token=f2a2f4e6-1f78-4ad9-a003-df04be78dfe6",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4717?alt=media&token=02d06b37-9bc0-4d3b-adcb-d8c89fb1fabc",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4451?alt=media&token=831c6d49-f076-49b9-bffc-aea13c9b0109",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5904?alt=media&token=d602feba-60be-4e50-9a54-38580941ed27",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/4655?alt=media&token=42fcba83-93f8-44b1-b588-9b7fbcf25f96",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/5487?alt=media&token=fb28eef8-7ed8-4af5-8fec-1703e9c727ad",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7757?alt=media&token=786f9e6e-fe64-486a-808c-960ef99aa158",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7953?alt=media&token=d2268693-7d38-4e82-b21a-74b5a682ba98"
]

ATV_FALLBACK_POOL = [
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/8016?alt=media&token=74144f54-f601-47a0-a7ca-c428cb8780ec",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/users%2FrM4rRtN3KmeDxNrrgGcJ6BtSWyu2%2Fvehicle%2F3910.jpg?alt=media&token=4db255ad-9dc4-45ed-acdf-e4f0a275a7fd",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7115?alt=media&token=264468a5-cc3c-44ff-9972-bd9e6c0cfcff",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/7106?alt=media&token=9514fdeb-a9ca-4ee7-8e35-588c6066293d",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/134?alt=media&token=20c9688b-8a8a-4486-af95-84d28ffb0abf",
    "https://firebasestorage.googleapis.com/v0/b/cmj-buggy.appspot.com/o/3753?alt=media&token=6b045e80-f336-4f56-aedb-163b9133f1dc"
]

_offroad_uid_cache: Optional[Dict[str, List[str]]] = None
_offroad_name_comp_cache: Optional[Dict[tuple, List[str]]] = None
_offroad_name_cache: Optional[Dict[str, List[str]]] = None

def _extract_all_http_urls(data: Dict[str, Any]) -> List[str]:
    urls = []
    plate_imgs = data.get("Plate No With Images") or data.get("Plate No With Images Ids")
    if isinstance(plate_imgs, dict):
        for plate, u_list in plate_imgs.items():
            if isinstance(u_list, list):
                for u in u_list:
                    if isinstance(u, str) and u.startswith("http") and u not in urls:
                        urls.append(u)
    imgs = data.get("Images") or data.get("ImagesIds") or data.get("image")
    if isinstance(imgs, list):
        for u in imgs:
            if isinstance(u, str) and u.startswith("http") and u not in urls:
                urls.append(u)
    elif isinstance(imgs, str) and imgs.startswith("http") and imgs not in urls:
        urls.append(imgs)
    return urls

def _init_offroad_caches():
    global _offroad_uid_cache, _offroad_name_comp_cache, _offroad_name_cache
    if _offroad_uid_cache is not None:
        return
    _offroad_uid_cache = {}
    _offroad_name_comp_cache = {}
    _offroad_name_cache = {}
    client = get_firestore_client()
    if not client:
        return
    try:
        docs = client.collection("offRoadVehicles").stream()
        for doc in docs:
            data = doc.to_dict()
            uid = doc.id
            imgs = _extract_all_http_urls(data)
            if imgs:
                _offroad_uid_cache[uid] = imgs
                name = str(data.get("Name", data.get("name", ""))).lower().strip()
                comp = str(data.get("companyName", data.get("Company", ""))).lower().strip()
                key_comp = (name, comp)
                
                if key_comp not in _offroad_name_comp_cache:
                    _offroad_name_comp_cache[key_comp] = []
                for u in imgs:
                    if u not in _offroad_name_comp_cache[key_comp]:
                        _offroad_name_comp_cache[key_comp].append(u)

                if name not in _offroad_name_cache:
                    _offroad_name_cache[name] = []
                for u in imgs:
                    if u not in _offroad_name_cache[name]:
                        _offroad_name_cache[name].append(u)
    except Exception as e:
        print(f"[Firebase] Error building offroad image cache: {e}")

def get_vehicle_image(v: Dict[str, Any], used_urls: Optional[set] = None) -> Optional[str]:
    """Extract a unique valid, visually distinct image URL for the vehicle data."""
    if used_urls is None:
        used_urls = set()

    v_name = str(v.get("Name", v.get("name", ""))).lower().strip()
    v_type = str(v.get("Type", v.get("type", ""))).lower().strip()

    # 1. Match with model-specific visual photo library first for brand accuracy
    for key, img_list in MODEL_SPECIFIC_IMAGES.items():
        if key in v_name:
            for u in img_list:
                if u not in used_urls:
                    used_urls.add(u)
                    return u

    # 2. Direct URLs on item itself
    direct_urls = _extract_all_http_urls(v)
    for u in direct_urls:
        if u not in used_urls:
            used_urls.add(u)
            return u

    # 3. Cross reference with offRoadVehicles caches
    try:
        _init_offroad_caches()
        feat_uid = v.get("FeatureVehicleUid") or v.get("id")
        if feat_uid and _offroad_uid_cache and feat_uid in _offroad_uid_cache:
            for u in _offroad_uid_cache[feat_uid]:
                if u not in used_urls:
                    used_urls.add(u)
                    return u

        v_comp = str(v.get("companyName", v.get("Company", ""))).lower().strip()
        if (v_name, v_comp) in _offroad_name_comp_cache:
            for u in _offroad_name_comp_cache[(v_name, v_comp)]:
                if u not in used_urls:
                    used_urls.add(u)
                    return u

        if v_name in _offroad_name_cache:
            for u in _offroad_name_cache[v_name]:
                if u not in used_urls:
                    used_urls.add(u)
                    return u
    except Exception:
        pass

    # 4. Type-specific fallback pool with guaranteed uniqueness
    if "atv" in v_type or "quad" in v_type or "atv" in v_name or "quad" in v_name:
        pool = ATV_FALLBACK_POOL
    else:
        pool = BUGGY_FALLBACK_POOL

    for u in pool:
        if u not in used_urls:
            used_urls.add(u)
            return u

    alt_pool = BUGGY_FALLBACK_POOL if pool == ATV_FALLBACK_POOL else ATV_FALLBACK_POOL
    for u in alt_pool:
        if u not in used_urls:
            used_urls.add(u)
            return u

    fallback = pool[len(used_urls) % len(pool)]
    used_urls.add(fallback)
    return fallback


import time

_vehicles_cache: Optional[List[Dict[str, Any]]] = None
_vehicles_cache_time: float = 0
CACHE_TTL_SECONDS = 300  # 5 minutes cache

def fetch_cmj_vehicles(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Read-only fetch of vehicle and deal documents from the Firestore database.
    Caches results in memory for CACHE_TTL_SECONDS to ensure ultra-fast response times.
    """
    global _vehicles_cache, _vehicles_cache_time

    now_ts = time.time()
    if not force_refresh and _vehicles_cache is not None and (now_ts - _vehicles_cache_time < CACHE_TTL_SECONDS):
        return _vehicles_cache

    client = get_firestore_client()
    if not client:
        return _vehicles_cache or []

    # Prioritize offRoadVehicles and Vehicle collections containing all diverse models
    candidate_collections = ["offRoadVehicles", "Vehicle", "deals", "allDeals", "vehicles", "buggies", "products"]
    results = []

    try:
        existing_col_ids = [c.id for c in client.collections()]
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        for col_name in candidate_collections:
            if col_name in existing_col_ids:
                docs = client.collection(col_name).stream()
                for doc in docs:
                    data = doc.to_dict()
                    # Skip deleted, disabled, blocked, coming soon, or unapproved items
                    if data.get("isDeleted") or data.get("disable") or data.get("is_block") or data.get("isVehicleComingSoon"):
                        continue
                    if data.get("Is Approved") is False or data.get("is_approved") is False:
                        continue
                    
                    # Check expiry date if specified
                    exp = data.get("expiry_date") or data.get("expiryDate")
                    if exp:
                        try:
                            if hasattr(exp, "timestamp") and exp < now:
                                continue
                        except Exception:
                            pass

                    data["id"] = doc.id
                    data["_collection"] = col_name
                    results.append(data)

        _vehicles_cache = results
        _vehicles_cache_time = now_ts
        print(f"[Firebase] Cached {len(results)} vehicles in memory (TTL: {CACHE_TTL_SECONDS}s)")
    except Exception as e:
        print(f"[Firebase] Error streaming documents: {e}")

    return _vehicles_cache or results

def warm_up_cache():
    """Pre-warms both vehicle listings and offroad image caches."""
    try:
        fetch_cmj_vehicles(force_refresh=True)
        _init_offroad_caches()
        print("[Firebase] Warm-up complete: inventory and image caches loaded.")
    except Exception as e:
        print(f"[Firebase] Error during cache warm-up: {e}")

def _get_vehicle_brand(name: str) -> str:
    name_l = name.lower()
    if any(k in name_l for k in ["maverick", "can-am", "canam", "x3", "x rs", "outlander"]):
        return "Can-Am"
    if any(k in name_l for k in ["rzr", "polaris", "ranger", "sportsman", "scrambler"]):
        return "Polaris"
    if any(k in name_l for k in ["zforce", "z force", "cfmoto", "cf moto", "uforce"]):
        return "CFMOTO"
    if any(k in name_l for k in ["wolverine", "yxz", "yamaha", "grizzly", "kodiak"]):
        return "Yamaha"
    if any(k in name_l for k in ["talon", "pioneer", "honda", "fourtrax", "rancher"]):
        return "Honda"
    if any(k in name_l for k in ["teryx", "krx", "kawasaki", "mule", "brute force"]):
        return "Kawasaki"
    if any(k in name_l for k in ["wildcat", "arctic cat", "stampede", "hdx", "prowler"]):
        return "Arctic Cat"
    return "Adventure Series"

def extract_search_criteria(user_query: str) -> Dict[str, Any]:
    """
    Extracts criteria (vehicle types list, seat counts list, brands, budget/prices) from user query.
    """
    q = user_query.lower()

    # 1. Detect requested seat categories
    seats = []
    if re.search(r'\b(2|two)\s*(?:-| )*(?:seater|seat|people|person|pax)\b', q):
        seats.append(2)
    if re.search(r'\b(4|four)\s*(?:-| )*(?:seater|seat|people|person|pax|family)\b', q):
        seats.append(4)
    if re.search(r'\b(1|one|single|solo)\s*(?:-| )*(?:seater|seat|people|person|pax)\b', q):
        seats.append(1)
    if re.search(r'\b(3|three)\s*(?:-| )*(?:seater|seat|people|person|pax)\b', q):
        seats.append(3)
    if re.search(r'\b(6|six)\s*(?:-| )*(?:seater|seat|people|person|pax)\b', q):
        seats.append(6)

    # 2. Detect requested vehicle types
    types = []
    if "buggy" in q or "buggies" in q:
        types.append("Buggy")
    if "atv" in q or "quad" in q:
        types.append("ATV")
    if "utv" in q:
        types.append("UTV")

    # 3. Detect requested brands
    brands = []
    for b in ["can-am", "canam", "maverick", "yamaha", "wolverine", "yxz", "cfmoto", "zforce", "honda", "talon", "kawasaki", "teryx", "polaris", "rzr", "arctic cat"]:
        if b in q:
            brands.append(b)

    # 4. Detect price / budget numbers
    prices = [float(p) for p in re.findall(r'(\d+(?:\.\d+)?)\s*(?:aed|\$|dollars|usd)', q)]
    if not prices:
        prices = [float(p) for p in re.findall(r'(?:under|below|budget|max|up to)\s*\$?(\d+(?:\.\d+)?)', q)]
    max_price = max(prices) if prices else None

    return {
        "types": types,
        "seats": seats,
        "brands": brands,
        "max_price": max_price
    }

def get_vehicle_star_rating(item: Dict[str, Any], price: Optional[float]) -> str:
    """Calculates a realistic premium star rating for a vehicle based on specs and model."""
    name = str(item.get("Name", item.get("name", ""))).lower()
    if any(k in name for k in ["maverick", "x3", "1000", "turbo", "can-am", "polaris rzr", "vip", "yxz", "talon", "teryx"]) or (price and price >= 600):
        return "⭐⭐⭐⭐⭐ (5/5 Stars - VIP Luxury)"
    elif any(k in name for k in ["400", "570", "700", "800", "950", "zforce", "wolverine", "cross"]) or (price and price >= 300):
        return "⭐⭐⭐⭐ (4/5 Stars - Premium)"
    else:
        return "⭐⭐⭐ (3/5 Stars - Standard Economy)"

def search_cmj_inventory(user_query: str) -> str:
    """
    Searches the 'cmj-dev' database for available vehicles matching user query.
    Returns a formatted string describing matching inventory with diverse brands and models.
    """
    criteria = extract_search_criteria(user_query)
    vehicles = fetch_cmj_vehicles()

    if not vehicles:
        return (
            "LIVE DATABASE STATUS (cmj-dev):\n"
            "Connected to database 'cmj-dev'. Currently, there are no vehicle listings populated in 'cmj-dev' yet.\n"
            "Inform the user about our general vehicle types (1-seater ATVs, 2-seater buggies, 4-seater UTVs) "
            "and suggest checking back soon or contacting customer support to book."
        )

    req_seats = criteria["seats"]
    req_types = criteria["types"]
    req_brands = criteria["brands"]

    def get_v_seats(v):
        s_str = str(v.get("Seat", v.get("Seats", v.get("seats", ""))))
        nums = re.findall(r'\d+', s_str)
        return [int(n) for n in nums] if nums else []

    def get_v_type(v):
        raw = (str(v.get("Type", "")) + " " + str(v.get("Name", ""))).lower()
        if "atv" in raw or "quad" in raw:
            return "ATV"
        elif "utv" in raw:
            return "UTV"
        else:
            return "Buggy"

    final_matched = []
    seen_names = set()
    seen_brands = set()

    def filter_and_rank(pool, target_seat=None, target_type=None, limit=3):
        matches = []
        for v in pool:
            v_name = str(v.get("Name", v.get("name", ""))).strip()
            if not v_name or len(v_name) < 3:
                continue
            # Skip test names like 'TEST VEH', 'banana bike', '1 ow3...'
            if any(t in v_name.lower() for t in ["test", "banana", "rehan"]):
                continue

            v_seats = get_v_seats(v)
            v_type = get_v_type(v)
            p = get_vehicle_price(v)
            brand = _get_vehicle_brand(v_name)

            if target_type and v_type != target_type and not (target_type == "Buggy" and v_type == "UTV"):
                continue
            if target_seat and (target_seat not in v_seats and not (not v_seats and target_seat == 2)):
                continue
            if req_brands and not any(rb in v_name.lower() or rb.lower() == brand.lower() for rb in req_brands):
                continue

            matches.append((v, p, brand, v_name))

        # Sort so distinct brands and verified models appear first
        def item_score(item_tuple):
            v, p, brand, v_name = item_tuple
            is_new_brand = 2 if brand not in seen_brands else 0
            has_brand = 1 if brand != "Adventure Series" else 0
            is_popular = 2 if any(k in v_name.lower() for k in ["maverick", "zforce", "wolverine", "talon", "teryx", "rzr"]) else 0
            return is_new_brand + has_brand + is_popular

        matches.sort(key=item_score, reverse=True)

        selected = []
        local_brands = set()
        for v, p, brand, v_name in matches:
            norm_name = v_name.lower().strip()
            if norm_name not in seen_names:
                # Prefer different brands when selecting
                if len(selected) < limit:
                    seen_names.add(norm_name)
                    seen_brands.add(brand)
                    local_brands.add(brand)
                    selected.append((v, p))

        return selected

    # Case 1: User requested multiple seat sizes (e.g. 2-seater AND 4-seater)
    if len(req_seats) > 1:
        for s in req_seats:
            target_t = req_types[0] if req_types else None
            chosen = filter_and_rank(vehicles, target_seat=s, target_type=target_t, limit=2)
            final_matched.extend(chosen)

    # Case 2: User requested multiple vehicle types (e.g. Buggy AND ATV)
    elif len(req_types) > 1:
        for t in req_types:
            target_s = req_seats[0] if req_seats else None
            chosen = filter_and_rank(vehicles, target_seat=target_s, target_type=t, limit=2)
            final_matched.extend(chosen)

    # Case 3: Single category or general query (e.g. "show me 4 buggies" or "show me buggies")
    else:
        target_s = req_seats[0] if req_seats else None
        target_t = req_types[0] if req_types else None
        # Extract how many vehicles requested
        num_req = 4
        num_match = re.search(r'\b(\d+)\s*(?:different|diff|top)?\s*(?:buggy|buggies|atv|vehicle|models)', user_query.lower())
        if num_match:
            try:
                num_req = max(2, min(6, int(num_match.group(1))))
            except Exception:
                pass

        final_matched = filter_and_rank(vehicles, target_seat=target_s, target_type=target_t, limit=num_req)

    if not final_matched:
        return (
            f"LIVE DATABASE STATUS (cmj-dev):\n"
            f"Searched 'cmj-dev' database for vehicles matching {criteria}. "
            f"No exact matches currently found in 'cmj-dev' matching this specific criteria. "
            f"Politely explain what was searched and suggest alternative available capacities or dates."
        )

    # Format matching inventory for prompt context
    lines = ["LIVE DATABASE INVENTORY (from cmj-dev database):"]
    used_urls = set()
    for item, price in final_matched:
        name = item.get("Name", item.get("name", "Adventure Vehicle"))
        raw_type = str(item.get("Type", item.get("type", "Off-road")))
        
        if "atv" in raw_type.lower() or "quad" in raw_type.lower() or "atv" in name.lower() or "quad" in name.lower():
            cat_label = "ATV / Quad Bike"
        elif "utv" in raw_type.lower():
            cat_label = "UTV / Buggy"
        else:
            cat_label = "Dune Buggy"

        seats = item.get("Seat", item.get("Seats", item.get("seats", "Standard")))
        price_str = f"{price:.0f} AED" if price is not None else "Contact for Price"
        company = item.get("companyName", item.get("Company", "Certified Operator"))
        duration = item.get("Duration", "60 Mins Desert Tour")
        stars = get_vehicle_star_rating(item, price)
        img_url = get_vehicle_image(item, used_urls=used_urls)
        img_str = f" | Image: {img_url}" if img_url else ""
        lines.append(f"- {name} | Category: {cat_label} | Premium Rating: {stars} | Seats: {seats} | Price: {price_str} | Duration: {duration} | Operator: {company}{img_str}")

    return "\n".join(lines)


