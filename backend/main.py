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

llm_student = ChatGoogleGenerativeAI(
    model="gemini-flash-lite-latest",
    api_key=GEMINI_API_KEY
)

# Pydantic schema for API
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

from datetime import datetime

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = request.message
    history = request.history
    
    try:
        # Build history text
        history_text = ""
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Guide"
            history_text += f"{role}: {msg.get('content')}\n"

        # Fetch live vehicle inventory from cmj-dev database (read-only)
        live_inventory = search_cmj_inventory(user_query)

        # The Guide answers purely via Gemini with marketplace business logic context
        prompt_template = PromptTemplate.from_template(
            "You are the customer support assistant for atvandbuggy.com, a premier multi-vendor off-road adventure tourism and vehicle rental marketplace.\n"
            "Your purpose is to assist users with vehicle rentals (1-seater ATVs, 2-seater buggies, 4-seater UTVs), bookings, pricing and tax breakdowns, transportation options, promo codes, camp locations, advance lead-time rules, and digital QR ticket check-ins.\n\n"
            "{marketplace_knowledge}\n\n"
            "{live_inventory}\n\n"
            "YOUR RULES:\n"
            "1. Answer questions about vehicles, tours, pricing, bookings, transportation, and desert camps accurately based on the business rules and inventory above.\n"
            "2. When listing vehicle recommendations, you MUST explicitly state the Vehicle Category (e.g. 🏎️ Dune Buggy or 🏍️ ATV / Quad Bike) and the Premium Star Rating (e.g. ⭐ Premium Rating: ⭐⭐⭐⭐⭐ (5/5 Stars - VIP Luxury)) for EACH vehicle option listed from the inventory context. IMPORTANT: If the user asks for multiple categories or quantities (e.g. '2 different 2-seaters and 2 different 4-seaters', or 'ATVs and Buggies'), you MUST list all distinct options for EACH requested category from the inventory context. For EACH vehicle option, list its full details (Name, Category, Premium Star Rating, Seats, Price in AED, Operator) and immediately place its EXACT corresponding Image URL directly underneath using markdown: ![Vehicle Name](Image URL). EVERY vehicle listed MUST have its OWN UNIQUE image URL from the inventory context. NEVER reuse the same image URL for different vehicles!\n"
            "3. If a user asks about transportation, clearly explain the 3 options: Self-Drive ($0, camp GPS provided), Group Pickup (scheduled shift times, per-person fee), and Private Pickup (VIP driver, distance-based pricing in km).\n"
            "4. If a user asks about pricing, explain that total price is: (Vehicle Price - Promo Discount) + Transport Fee + Company Service Fee + VAT.\n"
            "5. If a user asks about booking confirmations, explain that each reserved vehicle unit gets a unique digital QR code on their ticket/PDF, which staff scan at the desert camp to unlock the vehicle.\n"
            "6. If a user asks about booking ahead, explain that vendors have a lead-time buffer (advance booking requirement) to prepare vehicles and guides, so last-minute bookings closer than the buffer are restricted.\n"
            "7. If the user asks about ANYTHING completely unrelated (like software coding, math, general science, politics, or recipes), politely refuse: 'I'm sorry, but I can only assist you with questions related to our ATV & Buggy rentals, tours, and platform.'\n"
            "8. Always answer directly in friendly, natural conversational sentences. Never output code, serializers, API schemas, or technical jargon.\n"
            "9. Be friendly, concise, and helpful.\n"
            "10. When listing vehicles with numbers in their model name (like 'RZR XP 1000' or 'MXU 250'), clearly separate the model name from the price so the user understands that '1000' is the model name/cc, and state the actual price clearly (e.g. 'RZR XP 1000 - Price: 100 AED').\n"
            "11. End your response cleanly without extra signatures or system tags.\n\n"
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

        def build_inventory_fallback_response():
            lines = ["Here are the available vehicle options from our live inventory:\n"]
            # Parse inventory text for structured output
            inv_lines = [l.strip() for l in live_inventory.split("\n") if l.strip().startswith("- ")]
            if inv_lines:
                for idx, line in enumerate(inv_lines, 1):
                    parts = line.lstrip("- ").split(" | ")
                    info_parts = parts[0] if parts else line
                    
                    cat_val = "Off-road"
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
                
                lines.append("*(Note: '1000' in 'RZR XP 1000' refers to the 1000cc engine size, not the price!)*\n")
                lines.append("Feel free to ask about tour durations, self-drive vs pickup options, or booking steps!")
            else:
                lines.append("Currently, no active available vehicles match this exact criteria. Please ask about alternative vehicle types or budgets!")
            return "\n".join(lines)

        async def gemini_stream():
            try:
                async for chunk in llm_student.astream(prompt):
                    text_chunk = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    if isinstance(text_chunk, list):
                        text_chunk = "".join([str(item.get("text", item) if isinstance(item, dict) else item) for item in text_chunk])
                    if text_chunk:
                        yield str(text_chunk)
            except Exception as err:
                err_str = str(err)
                print(f"[Streaming Warning/Rate Limit] {err_str}")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    # Stream structured inventory fallback with images directly
                    yield build_inventory_fallback_response()
                else:
                    yield f"Sorry, I experienced a temporary error. {build_inventory_fallback_response()}"

        print(f"User asked: {user_query}")
        return StreamingResponse(gemini_stream(), media_type="text/plain")


    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred processing the chat.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
