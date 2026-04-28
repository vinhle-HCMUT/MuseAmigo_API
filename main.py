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


def seed_museums(db: Session) -> None:
    seed_data = [
        {
            "name": "Independence Palace",
            "operating_hours": "8:00 AM - 5:00 PM",
            "base_ticket_price": 30000,
            "latitude": 10.7769,
            "longitude": 106.6953,
        },
        {
            "name": "War Remnants Museum",
            "operating_hours": "7:30 AM - 6:00 PM",
            "base_ticket_price": 30000,
            "latitude": 10.7794,
            "longitude": 106.6920,
        },
        {
            "name": "HCMC Museum of Fine Arts",
            "operating_hours": "9:00 AM - 5:00 PM",
            "base_ticket_price": 30000,
            "latitude": 10.7716,
            "longitude": 106.6992,
        },
        {
            "name": "Ho Chi Minh City Museum",
            "operating_hours": "8:00 AM - 5:00 PM",
            "base_ticket_price": 30000,
            "latitude": 10.7767,
            "longitude": 106.7009,
        },
    ]

    for item in seed_data:
        existing = (
            db.query(models.Museum)
            .filter(models.Museum.name == item["name"])
            .first()
        )
        if existing:
            existing.operating_hours = item["operating_hours"]
            existing.base_ticket_price = item["base_ticket_price"]
            existing.latitude = item["latitude"]
            existing.longitude = item["longitude"]
        else:
            db.add(models.Museum(**item))

    db.commit()


def seed_artifacts(db: Session) -> None:
    seed_data = [
        # Independence Palace Artifacts
        {
            "artifact_code": "IP-001",
            "title": "Presidential Desk",
            "year": "1960s",
            "description": "The original presidential desk used by President Nguyễn Văn Thiệu during the Vietnam War. This desk witnessed many important historical decisions that shaped the future of South Vietnam.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_Presidential_Desk",
            "museum_id": 1  # Independence Palace
        },
        {
            "artifact_code": "IP-002", 
            "title": "T-54 Tank",
            "year": "1975",
            "description": "The famous T-54 tank that crashed through the gates of Independence Palace on April 30, 1975, symbolizing the end of the Vietnam War. This tank became an iconic symbol of reunification.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_T54_Tank",
            "museum_id": 1
        },
        {
            "artifact_code": "IP-003",
            "title": "Presidential Throne",
            "year": "1966",
            "description": "Elegant throne used in the Presidential Reception Hall. Crafted from fine Vietnamese woods and gold leaf, it represents the formal ceremonies of the Republic of Vietnam.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_Presidential_Throne",
            "museum_id": 1
        },
        # War Remnants Museum Artifacts
        {
            "artifact_code": "WRM-001",
            "title": "Guillotine",
            "year": "Early 1900s",
            "description": "A guillotine used during the French colonial period to execute Vietnamese revolutionaries. This somber artifact serves as a reminder of the struggles for independence.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Guillotine",
            "museum_id": 2  # War Remnants Museum
        },
        {
            "artifact_code": "WRM-002",
            "title": "Tiger Cages",
            "year": "1960s",
            "description": "Reconstruction of the infamous tiger cages used to imprison political prisoners during the war. These small cells represent the harsh conditions faced by detainees.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Tiger_Cages",
            "museum_id": 2
        },
        # Fine Arts Museum Artifacts
        {
            "artifact_code": "FAM-001",
            "title": "Lacquer Painting 'Rural Life'",
            "year": "1942",
            "description": "A beautiful lacquer painting depicting traditional Vietnamese rural scenes. Created by renowned artist Tô Ngọc Vân, showcasing the sophisticated lacquer techniques of Vietnamese artisans.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Lacquer_Painting",
            "museum_id": 3  # Fine Arts Museum
        },
        {
            "artifact_code": "FAM-002",
            "title": "Buddhist Statue",
            "year": "17th Century",
            "description": "Ancient bronze Buddhist statue from the Lê dynasty. This statue exemplifies the fine metalwork and religious artistry of traditional Vietnamese craftsmanship.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_Buddhist_Statue",
            "museum_id": 3
        },
        # HCMC Museum Artifacts
        {
            "artifact_code": "HCM-001",
            "title": "Traditional Ao Dai",
            "year": "1930s",
            "description": "An authentic traditional Vietnamese Ao Dai from the early 20th century. This elegant garment represents the cultural heritage and fashion evolution of Vietnamese women.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Ao_Dai",
            "museum_id": 4  # HCMC Museum
        },
        {
            "artifact_code": "HCM-002",
            "title": "Saigon Map 1930",
            "year": "1930",
            "description": "Historical map of Saigon from 1930, showing the city layout during French colonial period. This map provides insight into the urban development of early modern Saigon.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Saigon_Map",
            "museum_id": 4
        }
    ]

    for item in seed_data:
        existing = db.query(models.Artifact).filter(models.Artifact.artifact_code == item["artifact_code"]).first()
        if existing:
            # Update existing artifact
            existing.title = item["title"]
            existing.year = item["year"]
            existing.description = item["description"]
            existing.is_3d_available = item["is_3d_available"]
            existing.unity_prefab_name = item["unity_prefab_name"]
            existing.museum_id = item["museum_id"]
        else:
            db.add(models.Artifact(**item))

    db.commit()


def seed_exhibitions(db: Session) -> None:
    seed_data = [
        # Independence Palace Exhibitions
        {
            "name": "Presidential Office Tour",
            "location": "2nd Floor - Presidential Office",
            "museum_id": 1
        },
        {
            "name": "War History Gallery",
            "location": "Ground Floor - East Wing",
            "museum_id": 1
        },
        {
            "name": "Diplomatic Reception Hall",
            "location": "1st Floor - Central Hall",
            "museum_id": 1
        },
        # War Remnants Museum Exhibitions
        {
            "name": "War Crimes Exhibition",
            "location": "Building A - Upper Floor",
            "museum_id": 2
        },
        {
            "name": "International Support Gallery",
            "location": "Building B - Main Hall",
            "museum_id": 2
        },
        {
            "name": "Peace and Reconciliation Display",
            "location": "Outdoor Exhibition Area",
            "museum_id": 2
        },
        # Fine Arts Museum Exhibitions
        {
            "name": "Contemporary Vietnamese Art",
            "location": "Main Gallery - 1st Floor",
            "museum_id": 3
        },
        {
            "name": "Traditional Crafts Exhibition",
            "location": "Heritage Wing - 2nd Floor",
            "museum_id": 3
        },
        {
            "name": "International Art Collection",
            "location": "International Gallery - Ground Floor",
            "museum_id": 3
        },
        # HCMC Museum Exhibitions
        {
            "name": "Saigon History Timeline",
            "location": "Main Hall - Ground Floor",
            "museum_id": 4
        },
        {
            "name": "Traditional Culture Display",
            "location": "Cultural Wing - 2nd Floor",
            "museum_id": 4
        },
        {
            "name": "Urban Development Exhibition",
            "location": "Modern History Section - 1st Floor",
            "museum_id": 4
        }
    ]

    for item in seed_data:
        existing = db.query(models.Exhibition).filter(
            models.Exhibition.museum_id == item["museum_id"],
            models.Exhibition.name == item["name"]
        ).first()
        if existing:
            existing.location = item["location"]
        else:
            db.add(models.Exhibition(**item))

    db.commit()


def seed_routes(db: Session) -> None:
    seed_data = [
        # Independence Palace Routes
        {
            "name": "Presidential Tour",
            "estimated_time": "45 min",
            "stops_count": 6,
            "museum_id": 1
        },
        {
            "name": "Historical Highlights",
            "estimated_time": "30 min",
            "stops_count": 4,
            "museum_id": 1
        },
        {
            "name": "Architecture Tour",
            "estimated_time": "60 min",
            "stops_count": 8,
            "museum_id": 1
        },
        # War Remnants Museum Routes
        {
            "name": "War History Path",
            "estimated_time": "90 min",
            "stops_count": 12,
            "museum_id": 2
        },
        {
            "name": "Quick Overview",
            "estimated_time": "30 min",
            "stops_count": 5,
            "museum_id": 2
        },
        {
            "name": "Photography Tour",
            "estimated_time": "45 min",
            "stops_count": 7,
            "museum_id": 2
        },
        # Fine Arts Museum Routes
        {
            "name": "Masterpieces Collection",
            "estimated_time": "60 min",
            "stops_count": 8,
            "museum_id": 3
        },
        {
            "name": "Traditional Arts Walk",
            "estimated_time": "40 min",
            "stops_count": 6,
            "museum_id": 3
        },
        # HCMC Museum Routes
        {
            "name": "City History Journey",
            "estimated_time": "75 min",
            "stops_count": 10,
            "museum_id": 4
        },
        {
            "name": "Cultural Heritage Trail",
            "estimated_time": "50 min",
            "stops_count": 7,
            "museum_id": 4
        }
    ]

    for item in seed_data:
        existing = db.query(models.Route).filter(
            models.Route.museum_id == item["museum_id"],
            models.Route.name == item["name"]
        ).first()
        if existing:
            existing.estimated_time = item["estimated_time"]
            existing.stops_count = item["stops_count"]
        else:
            db.add(models.Route(**item))

    db.commit()


@app.on_event("startup")
def startup_seed_data():
    db = next(get_db())
    try:
        seed_museums(db)
        seed_artifacts(db)
        seed_exhibitions(db)
        seed_routes(db)
    finally:
        db.close()


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
    
    # Validation: Check if username and password are provided
    if not user.full_name or not user.full_name.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    if not user.password or not user.password.strip():
        raise HTTPException(status_code=400, detail="Password is required")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # 1. Package the data into our Database Model
    # (Note: For this test, we are saving the password as plain text. We will secure this later!)
    # 1. Tạo model (giữ nguyên)
    db_user = models.User(full_name=user.full_name.strip(), email=user.email.strip(), hashed_password=user.password)

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
    
    # Validation: Check if email and password are provided
    if not user_credentials.email or not user_credentials.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not user_credentials.password or not user_credentials.password.strip():
        raise HTTPException(status_code=400, detail="Password is required")
    
    # 1. Search the database for a user with this email
    db_user = db.query(models.User).filter(models.User.email == user_credentials.email.strip()).first()
    
    # 2. Check if the user exists AND if the plain text password matches
    # (Note: We are still using the column name 'hashed_password' from earlier, but it holds plain text right now)
    if not db_user or db_user.hashed_password != user_credentials.password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  
            detail="Invalid credentials"
        )
    
    # 3. Check if user has required fields (cleanup for existing users with no username/password)
    if not db_user.full_name or not db_user.full_name.strip():
        raise HTTPException(
            status_code=400,  
            detail="Your account is incomplete. Please contact support."
        )
        
    # 4. If everything matches, login is successful!
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
    
    # 1. Package the user's message with Ogima's system message
    system_message = (
        "You are Ogima, a friendly and helpful museum guide for the Independence Palace and other museums. "
        "Use your tools to find information about artifacts, museum hours, ticket prices, exhibitions, and routes. "
        "If you cannot find specific information in your database, politely say you don't know, "
        "but offer to help with other museum-related queries."
    )
    user_input = {"messages": [
        ("system", system_message),
        ("user", chat_request.message)
    ]}
    
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