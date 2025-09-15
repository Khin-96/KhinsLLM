#==========================
# agent.py
# KhinsGPT Agent with Persistent + Summarized Memory + Tool Logging + Vision
# Modified for Render deployment
# =========================

import os
import argparse
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# ---- LiveKit imports ----
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import google

# ---- Project imports ----
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION, is_called
from tools import get_weather, search_web, send_email, get_sports_score, tell_joke, set_timer, check_timer, random_fact, define_word, crypto_price
from music_tool import play_music, pause_music, resume_music, stop_music
from vision_tools import count_fingers, detect_objects, describe_scene, detect_faces, read_text
from speech_utils import process_speech

# ---- Memory imports ----
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logging.warning("mem0 package not available, using local memory only")

# ---- Web server imports ----
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import asyncio

# =========================
# Environment Setup
# =========================
load_dotenv()
logging.basicConfig(level=logging.INFO)

# =========================
# CLI Arguments
# =========================
parser = argparse.ArgumentParser()
parser.add_argument("--text-only", action="store_true", help="Disable audio/video and use text-only mode")
parser.add_argument("--no-vision", action="store_true", help="Disable computer vision capabilities")
parser.add_argument("--web-only", action="store_true", help="Run as web server only (no LiveKit)")
args, _ = parser.parse_known_args()

if args.text_only:
    os.environ['LIVEKIT_AGENTS_DISABLE_AUDIO'] = '1'
    print("Text-only mode enabled: Audio/video disabled")
else:
    os.environ.pop('LIVEKIT_AGENTS_DISABLE_AUDIO', None)
    print("Multimodal mode enabled: Audio, video, and text active")

# =========================
# LLM Setup
# =========================
try:
    llm_instance = google.beta.realtime.RealtimeModel(voice="Aoede", temperature=0.8)
    print("Using Google Realtime model (LiveKit-compatible)")
except Exception as e:
    logging.warning(f"Failed to initialize Google Realtime model: {e}")
    llm_instance = None

# =========================
# Memory Setup
# =========================
user_name = "Kinga"
MEMORY_FILE = "memory_store.json"

# Initialize mem0 client if available
if MEM0_AVAILABLE:
    mem0 = MemoryClient()
else:
    mem0 = None

def load_memory_file():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_memory_file(memories):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memories, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save memory file: {e}")

persistent_memories = load_memory_file()

def add_memory(text: str):
    # Try to use mem0 if available
    if mem0:
        try:
            mem0.add(text, user_id=user_name)
        except Exception as e:
            logging.warning("mem0.add() failed: %s", e)

    # Local memory storage
    if user_name not in persistent_memories:
        persistent_memories[user_name] = []

    persistent_memories[user_name].append({
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })

    if len(persistent_memories[user_name]) > 50:
        summarize_old_memories(user_name)

    save_memory_file(persistent_memories)
    logging.info(f"Saved memory: {text}")

def summarize_old_memories(user_id):
    old_memories = persistent_memories[user_id][:-20]
    combined_text = " ".join([m["text"] for m in old_memories])
    
    if mem0:
        try:
            summary = mem0.summarize(combined_text, user_id=user_id)
        except Exception as e:
            logging.warning("mem0.summarize() failed: %s", e)
            summary = " (failed to summarize older memories) "
    else:
        # Simple fallback summary
        summary = "Past conversations and interactions"
    
    persistent_memories[user_id] = [
        {"text": f"Summary of past: {summary}", "timestamp": datetime.utcnow().isoformat()}
    ] + persistent_memories[user_id][-20:]
    
    logging.info("Summarized older memories into a short note.")

def get_memory_summary():
    file_memories = persistent_memories.get(user_name, [])
    recent = [m["text"] for m in file_memories[-5:]]
    if not recent:
        return "No past memories yet."
    return "\n".join([f"- {m}" for m in recent])

# =========================
# Tools Setup
# =========================
# Base tools
base_tools = [
    get_weather,
    search_web,
    send_email,
    get_sports_score,
    tell_joke,
    set_timer,
    check_timer,
    random_fact,
    define_word,
    crypto_price,
    play_music,
    pause_music,
    resume_music,
    stop_music
]

# Vision tools (only include if not disabled and not in web-only mode)
vision_tools = []
if not args.no_vision and not args.web_only:
    vision_tools = [
        count_fingers,
        detect_objects,
        describe_scene,
        detect_faces,
        read_text
    ]
    print("Vision capabilities enabled")
else:
    print("Vision capabilities disabled")

# Combine all tools
tools = base_tools + vision_tools

# =========================
# Agent Definition
# =========================
class KhinsGPTAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=llm_instance,
            tts=google.TTS(
                voice_name="en-US-Neural2-C",
                language="en-US",
                gender="female"
            ) if not args.web_only else None,
            tools=tools,
        )
        self.current_mode = "chaotic"  # Track current mode for speech processing

    async def on_message(self, message):
        """
        Handles user messages with memory + tool support.
        """
        if message.role == "user":
            add_memory(f"User: {message.text}")

            # Check if user is changing modes
            user_text_lower = message.text.lower()
            if any(phrase in user_text_lower for phrase in ["nonchalant mode", "go chill", "chill mode"]):
                self.current_mode = "nonchalant"
            elif any(phrase in user_text_lower for phrase in ["chaotic mode", "be wild again"]):
                self.current_mode = "chaotic"
            elif "therapy" in user_text_lower:
                self.current_mode = "therapist"

            # Add memory context
            context = get_memory_summary()
            full_prompt = f"User said: {message.text}\n\nMemory context:\n{context}"

            try:
                reply = await self.generate(full_prompt)  # tool calls handled automatically
                
                # Process the reply to make it more natural
                natural_reply = process_speech(reply, self.current_mode)
                
                # If reply is empty (tool executed successfully), 
                # don't send an empty message
                if natural_reply.strip():
                    await self.send_message(natural_reply)
                    
            except Exception as e:
                logging.error("Agent generate failed: %s", e)
                # Only send error message if no tool was executed
                error_msg = "Um, sorry, I hit an error while thinking."
                await self.send_message(process_speech(error_msg, self.current_mode))

            add_memory(f"Assistant: {natural_reply if natural_reply.strip() else '[Tool executed silently]'}")

# =========================
# LiveKit Entry Point
# =========================
async def livekit_entrypoint(ctx: agents.JobContext):
    # Create the agent instance first
    agent = KhinsGPTAgent()
    
    session = AgentSession()
    room_options = RoomInputOptions(
        video_enabled=not args.text_only and not args.web_only,
        audio_enabled=not args.text_only and not args.web_only,
        text_enabled=True
    )

    try:
        await session.start(
            room=ctx.room,
            agent=agent,  # Use the agent instance we created
            room_input_options=room_options
        )
        await ctx.connect()
        print("🟢 KhinsGPT is live!")

        summary = get_memory_summary()
        greeting = process_speech(f"Hi {user_name}! I remember these about you:\n{summary}", "chaotic")
        await agent.send_message(greeting)

    except Exception as e:
        logging.warning(f"⚠️ Audio/Video failed, fallback to text-only: {e}")
        await session.start(
            room=ctx.room,
            agent=agent,  # Use the agent instance we created
            room_input_options=RoomInputOptions(video_enabled=False, audio_enabled=False, text_enabled=True)
        )
        await ctx.connect()
        print("🟡 Text-only fallback active")

# =========================
# Web Server Setup
# =========================
app = FastAPI(title="KhinsGPT Agent API")

@app.get("/")
async def root():
    return {"message": "KhinsGPT Agent API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "memory_entries": len(persistent_memories.get(user_name, []))}

@app.get("/memory")
async def get_memory():
    """Get current memory state"""
    return {
        "user": user_name,
        "memories": persistent_memories.get(user_name, []),
        "summary": get_memory_summary()
    }

@app.post("/chat")
async def chat_endpoint(message: str):
    """Chat with KhinsGPT via HTTP"""
    if not llm_instance:
        raise HTTPException(status_code=503, detail="LLM not initialized")
    
    # Add user message to memory
    add_memory(f"User (HTTP): {message}")
    
    # Create a simple agent instance for HTTP requests
    agent = KhinsGPTAgent()
    
    # Add memory context
    context = get_memory_summary()
    full_prompt = f"User said: {message}\n\nMemory context:\n{context}"
    
    try:
        reply = await agent.llm.generate(full_prompt)
        natural_reply = process_speech(reply, "chaotic")
        
        # Add assistant response to memory
        add_memory(f"Assistant: {natural_reply}")
        
        return {"response": natural_reply, "status": "success"}
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

# =========================
# Main Execution
# =========================
async def main():
    """Main entry point that handles both LiveKit and web server modes"""
    if args.web_only:
        # Run as web server only
        port = int(os.environ.get("PORT", 8000))
        print(f"🚀 Starting KhinsGPT web server on port {port}")
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        # Run as LiveKit worker
        print("🤖 Starting KhinsGPT as LiveKit worker")
        await agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=livekit_entrypoint))

if __name__ == "__main__":
    # Check if we're running in a web environment (like Render)
    if os.environ.get("RENDER", False) or args.web_only:
        asyncio.run(main())
    else:
        # Run as CLI application (original behavior)
        asyncio.run(agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=livekit_entrypoint)))