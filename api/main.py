import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", ".env")
load_dotenv(dotenv_path=env_path)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

try:
    from marketplace_knowledge import MARKETPLACE_KNOWLEDGE_PROMPT
    from firebase_service import search_cmj_inventory, warm_up_cache
except ImportError:
    from api.marketplace_knowledge import MARKETPLACE_KNOWLEDGE_PROMPT
    from api.firebase_service import search_cmj_inventory, warm_up_cache

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    import threading
    threading.Thread(target=warm_up_cache, daemon=True).start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = CURRENT_DIR if os.path.exists(os.path.join(CURRENT_DIR, "index.html")) else os.path.dirname(CURRENT_DIR)

for folder in ["css", "js", "assets"]:
    f_path = os.path.join(ROOT_DIR, folder)
    if os.path.exists(f_path):
        app.mount(f"/{folder}", StaticFiles(directory=f_path), name=folder)

@app.get("/")
async def serve_root():
    index_file = os.path.join(ROOT_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ATV & Buggy Chatbot API is Running"}

@app.get("/index.html")
async def serve_index():
    index_file = os.path.join(ROOT_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ATV & Buggy Chatbot API is Running"}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

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
            inv_lines = [l.strip() for l in live_inventory.split("\n") if l.strip().startswith("- ")]
            if not inv_lines:
                return "Currently, no active available vehicles match this exact criteria. Please ask about alternative vehicle types or budgets!"

            q = user_query.lower()
            if "atv" in q or "quad" in q:
                intro = "ATVs and Quad Bikes offer a solo desert adventure experience, perfect for thrill-seekers who love off-road riding. At atvandbuggy.com, all vehicles come with certified operators and full safety gear. Here are the available options:\n"
            elif any(x in q for x in ["4", "four", "family", "utv"]):
                intro = "Our 4-seater UTVs are perfect for families and groups to explore the UAE desert together in one powerful vehicle. Every booking includes safety briefing, protective gear, and a certified desert guide. Here are the available options:\n"
            else:
                intro = "Dune buggies offer an adrenaline-packed 2-person adventure across the UAE's stunning desert landscape. At atvandbuggy.com, certified operators ensure safety and excitement with every ride. Here are the available options:\n"

            lines = [intro]
            for idx, line in enumerate(inv_lines, 1):
                parts = line.lstrip("- ").split(" | ")
                info_parts = parts[0] if parts else line
                cat_val = "Dune Buggy"
                rating_val = "⭐⭐⭐⭐ (4/5 Stars - Premium)"
                price_val = "Contact for Price"
                duration_val = ""
                operator_val = ""
                img_url = None
                for p in parts[1:]:
                    if p.startswith("Category: "):
                        cat_val = p.replace("Category: ", "").strip()
                    elif p.startswith("Premium Rating: "):
                        rating_val = p.replace("Premium Rating: ", "").strip()
                    elif p.startswith("Price: "):
                        price_val = p.replace("Price: ", "").strip()
                    elif p.startswith("Duration: "):
                        duration_val = p.replace("Duration: ", "").strip()
                    elif p.startswith("Operator: "):
                        operator_val = p.replace("Operator: ", "").strip()
                    elif p.startswith("Image: "):
                        img_url = p.replace("Image: ", "").strip()
                dur_str = f" ({duration_val})" if duration_val else ""
                op_str = f" by {operator_val}" if operator_val else ""
                lines.append(f"{idx}. **{info_parts}** ({cat_val}){op_str}")
                lines.append(f"   ⭐ **Premium Tier:** {rating_val}")
                lines.append(f"   💰 **Price:** {price_val}{dur_str}")
                if img_url:
                    lines.append(f"![{info_parts}]({img_url})")
                lines.append("")
            lines.append("Feel free to ask about tour durations, pickup options, or how to book! 🏜️")
            return "\n".join(lines)

        # Check if API Key is configured
        if not current_key or current_key == "YOUR_GEMINI_API_KEY_HERE":
            async def missing_key_stream():
                yield "⚠️ **Setup Required on Vercel:** GEMINI_API_KEY environment variable is missing.\n\n"
                yield "Please go to **Vercel Dashboard -> Project Settings -> Environment Variables** and add `GEMINI_API_KEY`.\n\n"
                yield build_inventory_fallback_response()
            return StreamingResponse(missing_key_stream(), media_type="text/plain")

        prompt_template = PromptTemplate.from_template(
            "You are the friendly customer support assistant for atvandbuggy.com, a premier multi-vendor off-road adventure tourism marketplace in the UAE.\n"
            "Your purpose is to assist users with vehicle rentals (1-seater ATVs, 2-seater buggies, 4-seater UTVs), bookings, pricing, transportation options, promo codes, and digital QR ticket check-ins.\n\n"
            "{marketplace_knowledge}\n\n"
            "{live_inventory}\n\n"
            "YOUR STRICT RULES:\n"
            "1. Answer based only on the business rules and inventory data above. Be friendly, accurate, and concise.\n"
            "2. ALWAYS start your response with EXACTLY 2 sentences of friendly context about the vehicle type or activity the user asked about (e.g. 'Dune buggies offer an exciting 2-person desert adventure perfect for couples and friends. At atvandbuggy.com, you can book a certified operator with full safety gear included.'). Do NOT skip this intro.\n"
            "3. When listing vehicles: For EVERY single vehicle you mention, you MUST immediately follow it with its image using markdown format: ![Vehicle Name](Image URL). Use the EXACT Image URL from the inventory context. Do NOT skip any vehicle's image. Do NOT use the same image for two different vehicles.\n"
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

        FAST_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview"]

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
                        print(f"[Gemini Model {model_name}] Status {r.status_code}")
                except Exception as err:
                    print(f"[Gemini Model {model_name} Error] {err}")
                    if streamed_any:
                        return
                    continue

            # If all Gemini models failed or timed out, yield instant live database fallback
            yield build_inventory_fallback_response()

        print(f"User asked: {user_query}")
        return StreamingResponse(gemini_stream(), media_type="text/plain")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred processing the chat.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
