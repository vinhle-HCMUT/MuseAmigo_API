import os
import json
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

system_message = (
    "You are Ogima, the friendly virtual assistant for the MuseAmigo app. You must ALWAYS reply in JSON format with two keys: 'reply' and 'action'."
    "Your job is to help visitors explore museums. "
    "Always use the provided tools to get accurate information about artifacts, "
    "museum hours, exhibitions, and routes before answering."
    "If the user wants to go somewhere (toilet, exit, specific artifact), set action type to 'NAVIGATE'. "
    "If the user wants to change settings (theme, language), set action type to 'SETTINGS_UPDATE'. "
    "If no action is needed, set action to null."
)

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
def get_exhibition_details(exhibition_name: str) -> str:
    """Provides details about a specific exhibition, including which artifacts are included."""
    db = SessionLocal()
    try:
        exhibition = db.query(models.Exhibition).filter(models.Exhibition.name.ilike(f"%{exhibition_name}%")).first()
        if not exhibition:
            return f"I couldn't find an exhibition named '{exhibition_name}'."
        
        # Assuming the artifacts are stored as a comma-separated string of artifact codes
        artifact_codes = exhibition.artifacts.split(",") if exhibition.artifacts else []
        artifacts_info = []
        
        for code in artifact_codes:
            artifact = db.query(models.Artifact).filter(models.Artifact.artifact_code == code.strip()).first()
            if artifact:
                artifacts_info.append(f"{artifact.title} (Code: {artifact.artifact_code})")
        
        if artifacts_info:
            return f"Exhibition '{exhibition.name}' includes the following artifacts:\n" + "\n".join(artifacts_info)
        else:
            return f"Exhibition '{exhibition.name}' does not have any listed artifacts."
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
                count = 0
                raw = (r.stops_json or "").strip()
                if raw:
                    try:
                        loaded = json.loads(raw)
                        if isinstance(loaded, list):
                            count = len(loaded)
                    except Exception:
                        count = 0
                reply += f"- {r.name}: {r.estimated_time}, {count} stops.\n"
            return reply
        else:
            return f"There are no navigation routes listed for {museum.name}."
    finally:
        db.close()

@tool
def update_user_settings(user_id: int, theme: str = None, language: str = None, font_size: str = None, scheme: str = None) -> str:
    """Updates the user settings for the given user_id. You can update one or more of theme, language, font_size, and scheme."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return f"User with ID {user_id} not found."

        updated_fields = []
        if theme is not None:
            user.theme = theme
            updated_fields.append("theme")
        if language is not None:
            user.language = language
            updated_fields.append("language")
        if font_size is not None:
            user.font_size = font_size
            updated_fields.append("font_size")
        if scheme is not None:
            user.scheme = scheme
            updated_fields.append("scheme")

        if not updated_fields:
            return "No valid settings provided to update."

        db.commit()
        return f"Successfully updated settings: {', '.join(updated_fields)} for user {user_id}."
    except Exception as e:
        db.rollback()
        return f"An error occurred while updating settings: {e}"
    finally:
        db.close()

# 3. Initialize the Gemini brain
base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)

# 4. Give the AI the list of tools it is allowed to use
tools = [get_artifact_details, get_museum_info, get_exhibitions, get_exhibition_details, get_routes, update_user_settings]


# 5. Create the Agent Executor (The Manager!)
# This wraps the LLM and the tools together so it can run the loop automatically.
# Using the basic version without system message for now
agent_executor = create_react_agent(
    base_llm,
    tools,
    prompt=system_message # Thêm tính cách cho Agent
)


def get_ogima_response(message_text: str) -> str:
    """
    Hàm dùng chung để lấy câu trả lời từ Agent.
    """
    system_message = (
        "You are Ogima, a friendly and helpful museum guide for the Independence Palace and other museums. "
        "Use your tools to find information about artifacts, museum hours, ticket prices, exhibitions, and routes. "
        "If you cannot find specific information in your database, politely say you don't know, "
        "but offer to help with other museum-related queries. Keep your answers concise and spoken-friendly."
    )

    user_input = {"messages": [
        ("system", system_message),
        ("user", message_text)
    ]}

    # Chạy Agent
    final_state = agent_executor.invoke(user_input)
    raw_content = final_state["messages"][-1].content

    # Xử lý trường hợp content là list (như lỗi bạn gặp lúc nãy)
    if isinstance(raw_content, list):
        ai_reply = next((item['text'] for item in raw_content if item.get('type') == 'text'), "")
    else:
        ai_reply = str(raw_content)

    return ai_reply


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