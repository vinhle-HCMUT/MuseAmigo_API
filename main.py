from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, get_db
import uuid
from datetime import date
from agent import agent_executor
from sqlalchemy.exc import IntegrityError

# Creates the tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Your old test routes ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the MuseAmigo API!"}

@app.get("/museums/independence-palace")
def get_museum_info():
    return {"name": "Independence Palace"}

# --- NEW: Registration Endpoint ---
@app.post("/auth/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    # 1. Package the data into our Database Model
    # (Note: For this test, we are saving the password as plain text. We will secure this later!)
    # 1. Tạo model (giữ nguyên)
    db_user = models.User(full_name=user.full_name, email=user.email, hashed_password=user.password)

    try:
        # Đưa cả add và commit vào trong
        db.add(db_user)
        db.commit()
        # Refresh ngay sau khi commit thành công để lấy ID
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email này đã có chủ rồi bạn ơi!")
    except Exception as e:
        db.rollback()
        # Có thể in lỗi ra terminal để bạn dễ debug: print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống rồi, đợi tý nhé!")

    return db_user
@app.post("/auth/login")
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    
    # 1. Search the database for a user with this email
    db_user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    
    # 2. Check if the user exists AND if the plain text password matches
    # (Note: We are still using the column name 'hashed_password' from earlier, but it holds plain text right now)
    if not db_user or db_user.hashed_password != user_credentials.password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  
            detail="Invalid credentials"
        )
        
    # 3. If everything matches, login is successful!
    return {
        "message": "Login successful!", 
        "user_id": db_user.id, 
        "full_name": db_user.full_name
    }

# 1. Endpoint to load the Map/Discovery screen
@app.get("/museums", response_model=list[schemas.MuseumResponse])
def get_all_museums(db: Session = Depends(get_db)):
    museums = db.query(models.Museum).all()
    return museums

# 2. Endpoint to load the 3D Artifact screen after scanning a QR code
@app.get("/artifacts/{artifact_code}", response_model=schemas.ArtifactResponse)
def get_artifact(artifact_code: str, db: Session = Depends(get_db)):
    # Search for the exact code (e.g., "T54-843")
    artifact = db.query(models.Artifact).filter(models.Artifact.artifact_code == artifact_code).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Artifact not found"
        )
        
    return artifact

@app.post("/collections", response_model=schemas.CollectionResponse)
def add_to_collection(collection: schemas.CollectionCreate, db: Session = Depends(get_db)):
    
    # 1. Check if the user has already collected this artifact
    existing_item = db.query(models.Collection).filter(
        models.Collection.user_id == collection.user_id,
        models.Collection.artifact_id == collection.artifact_id
    ).first()
    
    # 2. If it already exists, throw an error to prevent duplicates
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Artifact already unlocked in your collection!"
        )
        
    # 3. If it's new, package the data into the Database Model
    new_collection_item = models.Collection(
        user_id=collection.user_id, 
        artifact_id=collection.artifact_id
    )
    
    # 4. Save to MySQL
    db.add(new_collection_item)
    db.commit()
    db.refresh(new_collection_item)
    
    return new_collection_item

# 1. Fetch Exhibitions for a specific museum (for the Home Screen)
@app.get("/museums/{museum_id}/exhibitions", response_model=list[schemas.ExhibitionResponse])
def get_exhibitions(museum_id: int, db: Session = Depends(get_db)):
    exhibitions = db.query(models.Exhibition).filter(models.Exhibition.museum_id == museum_id).all()
    return exhibitions

# 2. Purchase a Ticket and generate a QR Code
@app.post("/tickets/purchase", response_model=schemas.TicketResponse)
def purchase_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    
    # Generate a unique, random string for the QR code
    # Example output: "MUSEUM-1-USER-1-A8F3B92C"
    random_string = uuid.uuid4().hex[:8].upper()
    unique_qr = f"MUSEUM-{ticket.museum_id}-USER-{ticket.user_id}-{random_string}"
    
    # Get today's date
    today_date = str(date.today())

    # Create the database entry
    new_ticket = models.Ticket(
        ticket_type=ticket.ticket_type,
        purchase_date=today_date,
        qr_code=unique_qr,
        user_id=ticket.user_id,
        museum_id=ticket.museum_id
    )
    
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    
    return new_ticket

# --- PHASE 3: Fetch Navigation Routes ---
@app.get("/museums/{museum_id}/routes", response_model=list[schemas.RouteResponse])
def get_routes(museum_id: int, db: Session = Depends(get_db)):
    routes = db.query(models.Route).filter(models.Route.museum_id == museum_id).all()
    return routes

# --- PHASE 4: Calculate User Achievements ---
@app.get("/users/{user_id}/achievements")
def get_user_achievements(user_id: int, db: Session = Depends(get_db)):
    
    # 1. Count how many artifacts this user has in the collections table
    unlocked_items = db.query(models.Collection).filter(models.Collection.user_id == user_id).count()
    
    # 2. Calculate the score (Let's say each artifact gives 50 points)
    total_points = unlocked_items * 50
    
    # 3. Return the exact data Unity needs for the Achievements UI
    return {
        "user_id": user_id,
        "total_points": total_points,
        "unlocked_count": unlocked_items
    }

@app.put("/users/{user_id}/settings", response_model=schemas.UserResponse)
def update_user_settings(user_id: int, settings: schemas.UserSettingsUpdate, db: Session = Depends(get_db)):
    
    # 1. Find the user in the database
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # 2. If they don't exist, throw an error
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
        
    # 3. Update their preferences
    db_user.theme = settings.theme
    db_user.language = settings.language
    
    # 4. Save the changes to MySQL
    db.commit()
    db.refresh(db_user)
    
    return db_user

# --- PHASE 5: Ogima AI Chat Assistant ---
@app.post("/ai/chat", response_model=schemas.ChatResponse)
def chat_with_ogima(chat_request: schemas.ChatRequest):
    
    # 1. Package the user's message into the format LangGraph expects
    user_input = {"messages": [("user", chat_request.message)]}
    
    try:
        # 2. Run the AI loop (Think -> Search DB -> Generate Answer)
        final_state = agent_executor.invoke(user_input)
        
        # 3. Extract the final text reply
        ai_reply = final_state["messages"][-1].content
        
        # 4. Return it to Unity as JSON
        return {"reply": ai_reply}
        
    except Exception as e:
        # If the AI or Google's server crashes, we catch it so the app doesn't break
        raise HTTPException(status_code=500, detail=str(e))