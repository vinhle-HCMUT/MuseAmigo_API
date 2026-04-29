from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
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
    allow_origins=["*"],  # Allow all origins for development/testing
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
            "audio_asset": "assets/audio/artifact_001.wav",
            "museum_id": 1  # Independence Palace
        },
        {
            "artifact_code": "IP-002", 
            "title": "T-54 Tank",
            "year": "1975",
            "description": "The famous T-54 tank that crashed through the gates of Independence Palace on April 30, 1975, symbolizing the end of the Vietnam War. This tank became an iconic symbol of reunification.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_T54_Tank",
            "audio_asset": "assets/audio/artifact_002.wav",
            "museum_id": 1
        },
        {
            "artifact_code": "IP-003",
            "title": "Presidential Throne",
            "year": "1966",
            "description": "Elegant throne used in the Presidential Reception Hall. Crafted from fine Vietnamese woods and gold leaf, it represents the formal ceremonies of the Republic of Vietnam.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_Presidential_Throne",
            "audio_asset": "assets/audio/artifact_001.wav",
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
            "audio_asset": "assets/audio/artifact_002.wav",
            "museum_id": 2  # War Remnants Museum
        },
        {
            "artifact_code": "WRM-002",
            "title": "Tiger Cages",
            "year": "1960s",
            "description": "Reconstruction of the infamous tiger cages used to imprison political prisoners during the war. These small cells represent the harsh conditions faced by detainees.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Tiger_Cages",
            "audio_asset": "assets/audio/artifact_001.wav",
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
            "audio_asset": "assets/audio/artifact_002.wav",
            "museum_id": 3  # Fine Arts Museum
        },
        {
            "artifact_code": "FAM-002",
            "title": "Buddhist Statue",
            "year": "17th Century",
            "description": "Ancient bronze Buddhist statue from the Lê dynasty. This statue exemplifies the fine metalwork and religious artistry of traditional Vietnamese craftsmanship.",
            "is_3d_available": True,
            "unity_prefab_name": "Model_Buddhist_Statue",
            "audio_asset": "assets/audio/artifact_001.wav",
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
            "audio_asset": "assets/audio/artifact_002.wav",
            "museum_id": 4  # HCMC Museum
        },
        {
            "artifact_code": "HCM-002",
            "title": "Saigon Map 1930",
            "year": "1930",
            "description": "Historical map of Saigon from 1930, showing the city layout during French colonial period. This map provides insight into the urban development of early modern Saigon.",
            "is_3d_available": False,
            "unity_prefab_name": "Model_Saigon_Map",
            "audio_asset": "assets/audio/artifact_001.wav",
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
            existing.audio_asset = item["audio_asset"]
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

def seed_achievements(db: Session) -> None:
    seed_data = [
        # Global achievements (museum_id = NULL)
        {
            "name": "First Steps",
            "description": "Scan your first artifact",
            "requirement_type": "scan_count",
            "requirement_value": 1,
            "points": 50,
            "museum_id": None
        },
        {
            "name": "Artifact Collector",
            "description": "Scan 5 artifacts",
            "requirement_type": "scan_count",
            "requirement_value": 5,
            "points": 100,
            "museum_id": None
        },
        {
            "name": "Museum Explorer",
            "description": "Scan 10 artifacts",
            "requirement_type": "scan_count",
            "requirement_value": 10,
            "points": 200,
            "museum_id": None
        },
        {
            "name": "History Hunter",
            "description": "Discover 20 artifacts",
            "requirement_type": "scan_count",
            "requirement_value": 20,
            "points": 300,
            "museum_id": None
        },
        {
            "name": "Artifact Master",
            "description": "Discover 50 artifacts",
            "requirement_type": "scan_count",
            "requirement_value": 50,
            "points": 500,
            "museum_id": None
        },
        {
            "name": "Dynasty Master",
            "description": "Scan all artifacts in any single area/museum",
            "requirement_type": "area_complete",
            "requirement_value": 1,
            "points": 400,
            "museum_id": None
        },
        # Independence Palace achievements
        {
            "name": "Presidential History",
            "description": "Visit Independence Palace",
            "requirement_type": "museum_visit",
            "requirement_value": 1,
            "points": 100,
            "museum_id": 1
        },
        {
            "name": "Palace Explorer",
            "description": "Scan 3 artifacts at Independence Palace",
            "requirement_type": "museum_scan_count",
            "requirement_value": 3,
            "points": 150,
            "museum_id": 1
        },
        # War Remnants Museum achievements
        {
            "name": "War Historian",
            "description": "Visit War Remnants Museum",
            "requirement_type": "museum_visit",
            "requirement_value": 1,
            "points": 100,
            "museum_id": 2
        },
        {
            "name": "Peace Seeker",
            "description": "Scan 3 artifacts at War Remnants Museum",
            "requirement_type": "museum_scan_count",
            "requirement_value": 3,
            "points": 150,
            "museum_id": 2
        },
        # Fine Arts Museum achievements
        {
            "name": "Art Enthusiast",
            "description": "Visit Fine Arts Museum",
            "requirement_type": "museum_visit",
            "requirement_value": 1,
            "points": 100,
            "museum_id": 3
        },
        {
            "name": "Culture Lover",
            "description": "Scan 3 artifacts at Fine Arts Museum",
            "requirement_type": "museum_scan_count",
            "requirement_value": 3,
            "points": 150,
            "museum_id": 3
        },
        # HCMC Museum achievements
        {
            "name": "City Historian",
            "description": "Visit HCMC Museum",
            "requirement_type": "museum_visit",
            "requirement_value": 1,
            "points": 100,
            "museum_id": 4
        },
        {
            "name": "Heritage Guardian",
            "description": "Scan 3 artifacts at HCMC Museum",
            "requirement_type": "museum_scan_count",
            "requirement_value": 3,
            "points": 150,
            "museum_id": 4
        },
        {
            "name": "Museum Champion",
            "description": "Visit all 4 museums",
            "requirement_type": "all_museums",
            "requirement_value": 4,
            "points": 600,
            "museum_id": None
        }
    ]

    for item in seed_data:
        existing = db.query(models.Achievement).filter(
            models.Achievement.name == item["name"]
        ).first()
        if not existing:
            db.add(models.Achievement(**item))

    db.commit()


def migrate_add_audio_asset_column():
    """Add audio_asset column to artifacts table if it doesn't exist (for existing databases)"""
    db = next(get_db())
    try:
        # Try to add the column - will fail silently if it already exists
        db.execute(text("""
            ALTER TABLE artifacts ADD COLUMN audio_asset VARCHAR(200) DEFAULT '' 
        """))
        db.commit()
        print("✓ Added audio_asset column to artifacts table")
    except Exception as e:
        # Column likely already exists - this is fine
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ audio_asset column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup_seed_data():
    # Run migration first to ensure schema is up-to-date
    migrate_add_audio_asset_column()
    
    db = next(get_db())
    try:
        seed_museums(db)
        seed_artifacts(db)
        seed_exhibitions(db)
        seed_routes(db)
        seed_achievements(db)
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
    # Trim whitespace and make case-insensitive search
    clean_code = artifact_code.strip().upper()
    
    # First try exact match (case-insensitive via UPPER)
    artifact = db.query(models.Artifact).filter(
        func.upper(models.Artifact.artifact_code) == clean_code
    ).first()

    # If not found, try partial match in case there are spaces
    if not artifact:
        artifact = db.query(models.Artifact).filter(
            func.upper(func.replace(models.Artifact.artifact_code, ' ', '')) == clean_code.replace(' ', '')
        ).first()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Artifact code '{artifact_code}' not found. Available codes: IP-001, IP-002, IP-003, WRM-001, WRM-002, FAM-001, FAM-002, HCM-001, HCM-002"
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

# --- PHASE 3.5: Get Achievements for a Route ---
@app.get("/museums/{museum_id}/routes/{route_id}/achievements")
def get_route_achievements(museum_id: int, route_id: int, db: Session = Depends(get_db)):
    # Get achievements that are specific to this museum or global
    achievements = db.query(models.Achievement).filter(
        (models.Achievement.museum_id == museum_id) | (models.Achievement.museum_id == None)
    ).all()
    
    return {
        "route_id": route_id,
        "museum_id": museum_id,
        "achievements": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "points": a.points
            }
            for a in achievements
        ]
    }

# --- PHASE 3.6: Reset User Achievements for a Museum ---
@app.post("/users/{user_id}/achievements/reset/{museum_id}")
def reset_museum_achievements(user_id: int, museum_id: int, db: Session = Depends(get_db)):
    # Delete user achievements specific to this museum
    db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user_id,
        models.UserAchievement.museum_id == museum_id
    ).delete()
    
    db.commit()
    
    return {"message": f"Achievements reset for museum {museum_id}"}

# --- PHASE 4: Calculate User Achievements ---
@app.get("/users/{user_id}/achievements")
def get_user_achievements(user_id: int, db: Session = Depends(get_db)):
    
    # Get all available achievements
    all_achievements = db.query(models.Achievement).all()
    
    # Get user's completed achievements
    user_achievements = db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user_id
    ).all()
    
    # Create a dictionary of completed achievements by achievement_id
    completed_achievements = {
        ua.achievement_id: ua for ua in user_achievements
    }
    
    # Calculate total scan count per museum
    user_collections = db.query(models.Collection).filter(
        models.Collection.user_id == user_id
    ).all()
    
    artifact_ids = [c.artifact_id for c in user_collections]
    artifacts = db.query(models.Artifact).filter(models.Artifact.id.in_(artifact_ids)).all()
    
    museum_scan_counts = {}
    for artifact in artifacts:
        museum_scan_counts[artifact.museum_id] = museum_scan_counts.get(artifact.museum_id, 0) + 1
    
    total_scan_count = len(artifact_ids)
    unique_museums_visited = len(set(artifact.museum_id for artifact in artifacts))
    
    # Calculate total points from completed achievements
    total_points = sum(
        db.query(models.Achievement).filter(
            models.Achievement.id == ua.achievement_id
        ).first().points 
        for ua in user_achievements if ua.is_completed
    )
    
    # Check and update achievement progress
    achievements_response = []
    for achievement in all_achievements:
        is_completed = False
        progress = 0
        
        if achievement.id in completed_achievements:
            is_completed = completed_achievements[achievement.id].is_completed
        else:
            # Check if achievement should be completed
            if achievement.requirement_type == "scan_count":
                progress = min(total_scan_count, achievement.requirement_value)
                if total_scan_count >= achievement.requirement_value:
                    is_completed = True
            elif achievement.requirement_type == "museum_scan_count" and achievement.museum_id:
                progress = min(museum_scan_counts.get(achievement.museum_id, 0), achievement.requirement_value)
                if museum_scan_counts.get(achievement.museum_id, 0) >= achievement.requirement_value:
                    is_completed = True
            elif achievement.requirement_type == "museum_visit" and achievement.museum_id:
                if achievement.museum_id in museum_scan_counts:
                    is_completed = True
                    progress = 1
            elif achievement.requirement_type == "all_museums":
                progress = unique_museums_visited
                if unique_museums_visited >= achievement.requirement_value:
                    is_completed = True
            elif achievement.requirement_type == "area_complete":
                # Dynasty Master: Check if user has scanned all artifacts in any single museum
                for museum_id, count in museum_scan_counts.items():
                    total_artifacts_in_museum = db.query(models.Artifact).filter(
                        models.Artifact.museum_id == museum_id
                    ).count()
                    if count >= total_artifacts_in_museum:
                        is_completed = True
                        progress = 1
                        break
            
            # Auto-complete achievement if criteria met
            if is_completed and achievement.id not in completed_achievements:
                new_user_achievement = models.UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    museum_id=achievement.museum_id,
                    is_completed=True,
                    completed_at=str(date.today())
                )
                db.add(new_user_achievement)
                db.commit()
                total_points += achievement.points
        
        achievements_response.append({
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "requirement_type": achievement.requirement_type,
            "requirement_value": achievement.requirement_value,
            "points": achievement.points,
            "museum_id": achievement.museum_id,
            "is_completed": is_completed,
            "progress": progress
        })
    
    return {
        "user_id": user_id,
        "total_points": total_points,
        "unlocked_count": total_scan_count,
        "achievements": achievements_response
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