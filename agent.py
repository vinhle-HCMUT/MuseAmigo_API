import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
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

# 3. Initialize the Gemini brain
base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7 
)

# 4. Give the AI the list of tools it is allowed to use
tools = [get_artifact_details]

# 5. Create the Agent Executor (The Manager!)
# This wraps the LLM and the tools together so it can run the loop automatically.
agent_executor = create_react_agent(base_llm, tools)

# --- QUICK TEST ---
if __name__ == "__main__":
    print("Asking Ogima about the tank...")
    
    # LangGraph requires a dictionary with a "messages" list
    user_input = {"messages": [("user", "Can you tell me the history of the T-54 Tank No. 843?")]}
    
    # Run the full loop (Think -> Search Database -> Write Final Answer)
    final_state = agent_executor.invoke(user_input)
    
    print("\n===============================")
    print("FINAL RESPONSE TO UNITY APP:")
    # We grab the very last message in the conversation history, which is Ogima's final answer
    print(final_state["messages"][-1].content)