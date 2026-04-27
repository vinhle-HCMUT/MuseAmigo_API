import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from database import SessionLocal
import models
from langgraph.prebuilt import create_react_agent # We use the official LangGraph agent builder

# 1. Load the secret API key from the .env file
load_dotenv()

# 2. Verify the key exists so the server doesn't crash mysteriously later
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY is missing from the .env file!")

@tool
def get_artifact_details(query: str) -> str:
    """Searches the museum database for an artifact by its name or code and returns its details."""
    # Open a new database session
    db = SessionLocal()
    try:
        # Search the database for any artifact title or code that matches the AI's query
        artifact = db.query(models.Artifact).filter(
            (models.Artifact.title.ilike(f"%{query}%")) | 
            (models.Artifact.artifact_code.ilike(f"%{query}%"))
        ).first()
        
        # Format the result so the AI can read it easily
        if artifact:
            return f"Found: {artifact.title} (Code: {artifact.artifact_code}). Year: {artifact.year}. Description: {artifact.description}"
        else:
            return f"No artifact found matching '{query}'."
    finally:
        db.close() # Always close the database connection!

@tool
def get_museum_info(name: str) -> str:
    """Provides general information about a museum, such as operating hours and ticket prices."""
    db = SessionLocal()
    try:
        museum = db.query(models.Museum).filter(models.Museum.name.ilike(f"%{name}%")).first()
        if museum:
            return (f"Museum: {museum.name}. "
                    f"Operating Hours: {museum.operating_hours}. "
                    f"Ticket Price: {museum.base_ticket_price} VND. "
                    f"Location: {museum.latitude}, {museum.longitude}.")
        else:
            return f"I couldn't find any museum named '{name}'."
    finally:
        db.close()

@tool
def get_exhibitions(museum_name: str) -> str:
    """Lists all current exhibitions at a specific museum."""
    db = SessionLocal()
    try:
        museum = db.query(models.Museum).filter(models.Museum.name.ilike(f"%{museum_name}%")).first()
        if not museum:
            return f"I couldn't find a museum named '{museum_name}'."
        
        exhibitions = db.query(models.Exhibition).filter(models.Exhibition.museum_id == museum.id).all()
        if exhibitions:
            reply = f"Exhibitions at {museum.name}:\n"
            for ex in exhibitions:
                reply += f"- {ex.name} (Location: {ex.location})\n"
            return reply
        else:
            return f"There are currently no exhibitions listed for {museum.name}."
    finally:
        db.close()

@tool
def get_routes(museum_name: str) -> str:
    """Provides navigation routes available in a specific museum."""
    db = SessionLocal()
    try:
        museum = db.query(models.Museum).filter(models.Museum.name.ilike(f"%{museum_name}%")).first()
        if not museum:
            return f"I couldn't find a museum named '{museum_name}'."
        
        routes = db.query(models.Route).filter(models.Route.museum_id == museum.id).all()
        if routes:
            reply = f"Available routes at {museum.name}:\n"
            for r in routes:
                reply += f"- {r.name}: {r.estimated_time}, {r.stops_count} stops.\n"
            return reply
        else:
            return f"There are no navigation routes listed for {museum.name}."
    finally:
        db.close()

# 3. Initialize the Gemini brain
base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7 
)

# 4. Give the AI the list of tools it is allowed to use
tools = [get_artifact_details, get_museum_info, get_exhibitions, get_routes]

# 5. Create the Agent Executor (The Manager!)
# This wraps the LLM and the tools together so it can run the loop automatically.
# We add a system message to give the AI more context.
system_message = (
    "You are Ogima, a friendly and helpful museum guide for the Independence Palace and other museums. "
    "Use your tools to find information about artifacts, museum hours, ticket prices, exhibitions, and routes. "
    "If you cannot find specific information in your database, politely say you don't know, "
    "but offer to help with other museum-related queries."
)

# Try the newer approach with state_modifier
def modify_state(messages):
    return [SystemMessage(content=system_message)] + messages

agent_executor = create_react_agent(base_llm, tools, state_modifier=modify_state)

# --- QUICK TEST ---
if __name__ == "__main__":
    print("Asking Ogima about museum hours...")
    
    # Test museum info
    user_input = {"messages": [("user", "What are the operating hours of the Independence Palace?")]}
    final_state = agent_executor.invoke(user_input)
    print("\nRESPONSE (Hours):")
    print(final_state["messages"][-1].content)

    # Test routes
    print("\nAsking Ogima about routes...")
    user_input = {"messages": [("user", "Are there any routes in the Independence Palace?")]}
    final_state = agent_executor.invoke(user_input)
    print("\nRESPONSE (Routes):")
    print(final_state["messages"][-1].content)