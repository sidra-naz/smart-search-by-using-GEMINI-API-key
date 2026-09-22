import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from marketplace_knowledge import MARKETPLACE_KNOWLEDGE_PROMPT
from firebase_service import search_cmj_inventory, fetch_cmj_vehicles, warm_up_cache

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    import threading
    # Warm up Firestore vehicle and image caches asynchronously on server launch
    threading.Thread(target=warm_up_cache, daemon=True).start()

# Enable CORS so our frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only. In prod, specify the exact domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch Gemini API Key from .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("[WARNING] GEMINI_API_KEY is missing! Please add GEMINI_API_KEY=your_key in backend/.env file.")

# Model priority list — stable 1.5/2.0 first (less overloaded), then 3.x as fallback
FAST_MODELS = [
    "gemini-1.5-flash",          # stable, high quota
    "gemini-1.5-flash-8b",       # lightweight, reliable
    "gemini-2.0-flash",          # fast stable model
    "gemini-2.0-flash-exp",      # experimental but often available
    "gemini-3.6-flash",          # newer — often overloaded
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]

# Pydantic schema for API
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

from datetime import datetime

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = request.message
    history = request.history
    current_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    
    try:
        # Build history text
        history_text = ""
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Guide"
            history_text += f"{role}: {msg.get('content')}\n"

        # Fetch live vehicle inventory from cmj-dev database (read-only)
        live_inventory = search_cmj_inventory(user_query)

        def build_inventory_fallback_response():
            import re as _re
            inv_lines = [l.strip() for l in live_inventory.split("\n") if l.strip().startswith("- ")]
            if not inv_lines:
                return "Currently no vehicles match your criteria. Please try a different search!"

            q = user_query.lower()

            # ── Parse the user query to understand what they want ────────────────
            wants_atv    = any(w in q for w in ["atv", "quad", "quad bike"])
            wants_buggy  = any(w in q for w in ["buggy", "buggies", "dune buggy"])
            wants_utv    = any(w in q for w in ["utv", "4-seater", "4 seater", "four seater", "family"])
            wants_both   = wants_atv and (wants_buggy or wants_utv)

            # Extract price limit if mentioned (e.g. "under 500", "below 1000", "max 800")
            price_limit = None
            price_match = _re.search(r'(?:under|below|max|less than|up to)[\s:]*([\d,]+)', q)
            if price_match:
                try:
                    price_limit = float(price_match.group(1).replace(',', ''))
                except ValueError:
                    pass

            # Extract count hints per type  (e.g. "2 atv and 3 buggy")
            atv_count_match   = _re.search(r'(\d+)\s*(?:atv|quad)', q)
            buggy_count_match = _re.search(r'(\d+)\s*(?:buggy|buggies)', q)
            utv_count_match   = _re.search(r'(\d+)\s*(?:utv|4.seater)', q)
            atv_wanted   = int(atv_count_match.group(1))   if atv_count_match   else (2 if wants_atv   else 0)
            buggy_wanted = int(buggy_count_match.group(1)) if buggy_count_match else (2 if wants_buggy else 0)
            utv_wanted   = int(utv_count_match.group(1))   if utv_count_match   else (2 if wants_utv   else 0)

            # ── Parse all inventory vehicles into structured dicts ────────────────
            def parse_vehicle(line):
                parts = line.lstrip("- ").split(" | ")
                v = {
                    "name": parts[0].strip(),
                    "category": "Dune Buggy",
                    "rating": "⭐⭐⭐⭐ (4/5 Stars - Premium)",
                    "price_str": "Contact for Price",
                    "price_num": None,
                    "duration": "",
                    "operator": "",
                    "img_url": None,
                }
                for p in parts[1:]:
                    if p.startswith("Category: "):       v["category"]  = p[10:].strip()
                    elif p.startswith("Premium Rating: "): v["rating"]    = p[16:].strip()
                    elif p.startswith("Price: "):          v["price_str"] = p[7:].strip()
                    elif p.startswith("Duration: "):       v["duration"]  = p[10:].strip()
                    elif p.startswith("Operator: "):       v["operator"]  = p[10:].strip()
                    elif p.startswith("Image: "):          v["img_url"]   = p[7:].strip()
                # Parse numeric price from price string
                pm = _re.search(r'([\d,]+)', v["price_str"])
                if pm:
                    try: v["price_num"] = float(pm.group(1).replace(',', ''))
                    except: pass
                return v

            all_vehicles = [parse_vehicle(l) for l in inv_lines]

            # ── Filter by price if requested ─────────────────────────────────────
            if price_limit:
                all_vehicles = [v for v in all_vehicles
                                if v["price_num"] is None or v["price_num"] <= price_limit]

            # ── Classify vehicles ────────────────────────────────────────────────
            def is_atv(v):
                return any(w in v["category"].lower() for w in ["atv", "quad"])
            def is_buggy(v):
                return any(w in v["category"].lower() for w in ["buggy", "dune"])
            def is_utv(v):
                return any(w in v["category"].lower() for w in ["utv", "4", "four"])

            # ── Select the requested vehicles ────────────────────────────────────
            selected = []
            if wants_both or (not wants_atv and not wants_buggy and not wants_utv):
                # User wants a mix OR didn't specify type → split evenly
                atv_pool   = [v for v in all_vehicles if is_atv(v)]
                buggy_pool = [v for v in all_vehicles if is_buggy(v)]
                utv_pool   = [v for v in all_vehicles if is_utv(v)]
                if atv_wanted > 0:   selected += atv_pool[:atv_wanted]
                if buggy_wanted > 0: selected += buggy_pool[:buggy_wanted]
                if utv_wanted > 0:   selected += utv_pool[:utv_wanted]
                if not selected:     selected = all_vehicles[:4]
            elif wants_atv:
                selected = [v for v in all_vehicles if is_atv(v)][:atv_wanted or 4]
            elif wants_utv:
                selected = [v for v in all_vehicles if is_utv(v)][:utv_wanted or 4]
            else:
                selected = [v for v in all_vehicles if is_buggy(v)][:buggy_wanted or 4]

            if not selected:
                selected = all_vehicles[:4]  # safety net

            # ── Build the 2-sentence query-specific intro ────────────────────────
            price_str = f" under {int(price_limit)} AED" if price_limit else ""
            if wants_both:
                type_desc = f"{buggy_wanted or 2} Dune Bugg{'ies' if (buggy_wanted or 2)>1 else 'y'} and {atv_wanted or 2} ATV{'s' if (atv_wanted or 2)>1 else ''}"
                intro = (f"You're looking for {type_desc}{price_str} — here's exactly what we found on atvandbuggy.com from our live inventory. "
                         f"Dune Buggies seat 2 people for a shared adventure, while ATVs are solo 1-seater machines — both include safety gear and a certified operator:")
            elif wants_utv:
                intro = (f"Our 4-seater UTVs{price_str} are perfect for families and groups exploring the UAE desert together on atvandbuggy.com. "
                         f"Every booking includes a safety briefing, protective gear, and a certified desert guide — here are your options:")
            elif wants_atv:
                intro = (f"ATVs are powerful 1-seater off-road quad bikes{price_str} — perfect for solo riders who want maximum desert thrill on atvandbuggy.com. "
                         f"All rides come with helmet, safety gear, and operator guidance — here are the best matches:")
            else:
                intro = (f"Dune Buggies are exciting 2-seater off-road vehicles{price_str} — great for couples and friends on atvandbuggy.com's UAE desert trails. "
                         f"Every booking includes full safety gear, a certified operator, and desert navigation support — here are the available options:")

            # ── Render the response ──────────────────────────────────────────────
            lines = [intro, ""]
            for idx, v in enumerate(selected, 1):
                dur_str = f" ({v['duration']})" if v['duration'] else ""
                op_str  = f" by {v['operator']}" if v['operator'] else ""
                lines.append(f"{idx}. **{v['name']}** ({v['category']}){op_str}")
                lines.append(f"   ⭐ **Premium Tier:** {v['rating']}")
                lines.append(f"   💰 **Price:** {v['price_str']}{dur_str}")
                if v['img_url']:
                    lines.append(f"![{v['name']}]({v['img_url']})")
                lines.append("")

            lines.append("Feel free to ask about tour durations, pickup options, or how to book! 🏜️")
            return "\n".join(lines)

        # Check if API Key is configured
        if not current_key or current_key == "YOUR_GEMINI_API_KEY_HERE":
            async def missing_key_stream():
                yield "⚠️ **Setup Required:** GEMINI_API_KEY is missing in `.env`.\n\n"
                yield build_inventory_fallback_response()
            return StreamingResponse(missing_key_stream(), media_type="text/plain")

        # Determine quick context about what the user is asking for the intro
        q_lower = user_query.lower()
        if "atv" in q_lower or "quad" in q_lower:
            intro_hint = "ATV / Quad Bikes (1-seater solo off-road vehicles)"
        elif any(x in q_lower for x in ["4-seat", "4 seat", "four seat", "family", "utv"]):
            intro_hint = "4-Seater UTVs / Family Buggies"
        elif any(x in q_lower for x in ["2-seat", "2 seat", "two seat", "buggy", "buggies"]):
            intro_hint = "2-Seater Dune Buggies"
        else:
            intro_hint = "off-road adventure vehicles including ATVs and Dune Buggies"

        # The Guide answers purely via Gemini with marketplace business logic context
        prompt_template = PromptTemplate.from_template(
            "You are the friendly customer support assistant for atvandbuggy.com, a premier multi-vendor off-road adventure tourism marketplace in the UAE.\n"
            "Your purpose is to assist users with vehicle rentals (1-seater ATVs, 2-seater buggies, 4-seater UTVs), bookings, pricing, transportation options, promo codes, and digital QR ticket check-ins.\n\n"
            "{marketplace_knowledge}\n\n"
            "{live_inventory}\n\n"
            "YOUR STRICT RULES:\n"
            "1. Answer based only on the business rules and inventory data above. Be friendly, accurate, and concise.\n"
            "2. ALWAYS start your response with EXACTLY 2 sentences that directly explain what the user searched for. The sentences must reference the user's EXACT search terms (e.g. if they searched 'ATV under 500 AED', say 'ATVs are solo 1-seater off-road vehicles perfect for desert adventures, and we have options matching your 500 AED budget on atvandbuggy.com. Here are the best matches from our live inventory:'). Do NOT write a generic intro — it MUST reflect the specific query.\n"
            "3. When listing vehicles: For EVERY single vehicle you mention, you MUST immediately follow it with its image using markdown format: ![Vehicle Name](Image URL). Use the EXACT Image URL from the inventory context. Do NOT skip any vehicle's image. Do NOT reuse the same image URL for two different vehicles.\n"
            "4. For each vehicle listing, show: Name, Category (🏎️ Dune Buggy / 🏍️ ATV), Premium Star Rating (⭐), Seats, Price in AED, and Operator.\n"
            "5. If user asks about transportation, explain the 3 options: Self-Drive (free, GPS provided), Group Pickup (per-person fee), Private Pickup (VIP, distance-based km pricing).\n"
            "6. If user asks about pricing, explain total = (Vehicle Price - Promo) + Transport + Service Fee + VAT.\n"
            "7. If user asks about booking confirmations, explain each reserved vehicle gets a unique QR code scanned at the desert camp gate.\n"
            "8. If user asks about ANYTHING unrelated (coding, recipes, politics), politely refuse and redirect to ATV & Buggy topics.\n"
            "9. NEVER output raw code, API schemas, or technical jargon. Speak naturally.\n"
            "10. When models have numbers in the name (e.g. 'RZR XP 1000'), clarify that '1000' refers to engine cc size, not price.\n"
            "11. End cleanly without extra signatures.\n\n"
            "Conversation History:\n"
            "{history}\n\n"
            "User: {question}\nGuide:"
        )
        prompt = prompt_template.format(
            marketplace_knowledge=MARKETPLACE_KNOWLEDGE_PROMPT,
            live_inventory=live_inventory,
            history=history_text,
            question=user_query
        )

        import requests
        import json

        def gemini_stream():
            streamed_any = False
            for model_name in FAST_MODELS:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?alt=sse&key={current_key}"
                    r = requests.post(
                        url,
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                        stream=True,
                        timeout=30
                    )
                    if r.status_code == 200:
                        for line in r.iter_lines():
                            if line:
                                decoded = line.decode("utf-8")
                                if decoded.startswith("data: "):
                                    try:
                                        data_json = json.loads(decoded[6:])
                                        t = data_json["candidates"][0]["content"]["parts"][0]["text"]
                                        if t:
                                            streamed_any = True
                                            yield t
                                    except Exception:
                                        pass
                        if streamed_any:
                            return
                    else:
                        print(f"[Gemini Model {model_name}] Status {r.status_code}: {r.text[:200]}")
                except Exception as err:
                    print(f"[Gemini Model {model_name} Error] {err}")
                    if streamed_any:
                        return
                    continue

            # Fallback to database response if all Gemini models are unavailable
            yield build_inventory_fallback_response()

        print(f"User asked: {user_query}")
        return StreamingResponse(gemini_stream(), media_type="text/plain")


    except Exception as e:
        print(f"Error: {str(e)}__")
        raise HTTPException(status_code=500, detail="An error occurred processing the chat.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
