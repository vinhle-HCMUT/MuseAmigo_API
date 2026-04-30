from pydantic import BaseModel

# This is what we expect Unity to send us (The JSON payload)
class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str

# This is what we send back to Unity (Notice we DO NOT send the password back!)
class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    theme: str       
    language: str    
    class Config:
        from_attributes = True # This tells Pydantic it's okay to read data from a SQLAlchemy model

# The payload Unity sends for login
class UserLogin(BaseModel):
    email: str
    password: str

class MuseumResponse(BaseModel):
    id: int
    name: str
    operating_hours: str
    base_ticket_price: int
    
    latitude: float
    longitude: float
    
    class Config:
        from_attributes = True

class ArtifactResponse(BaseModel):
    id: int
    artifact_code: str
    title: str
    year: str
    description: str
    is_3d_available: bool
    museum_id: int
    
    unity_prefab_name: str
    audio_asset: str = ""
    class Config:
        from_attributes = True

# What Unity sends when the user scans an item
class CollectionCreate(BaseModel):
    user_id: int
    artifact_id: int

# What FastAPI returns to confirm it was saved
class CollectionResponse(BaseModel):
    id: int
    user_id: int
    artifact_id: int

    class Config:
        from_attributes = True

# --- EXHIBITIONS ---
class ExhibitionResponse(BaseModel):
    id: int
    name: str
    location: str
    museum_id: int

    class Config:
        from_attributes = True

# --- TICKETS ---
# What Unity sends when the user clicks "Pay"
class TicketCreate(BaseModel):
    user_id: int
    museum_id: int
    ticket_type: str  # e.g., "Adult", "Student"

# What FastAPI returns (including the newly generated QR Code!)
class TicketResponse(BaseModel):
    id: int
    ticket_type: str
    purchase_date: str
    qr_code: str
    is_used: bool
    user_id: int
    museum_id: int

    class Config:
        from_attributes = True

class RouteResponse(BaseModel):
    id: int
    name: str
    estimated_time: str
    stops_count: int
    museum_id: int

    class Config:
        from_attributes = True

class AchievementResponse(BaseModel):
    id: int
    name: str
    description: str
    requirement_type: str
    requirement_value: int
    points: int
    museum_id: int | None

    class Config:
        from_attributes = True

class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement_id: int
    museum_id: int | None
    is_completed: bool
    completed_at: str | None

    class Config:
        from_attributes = True

class UserSettingsUpdate(BaseModel):
    theme: str
    language: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# What Unity sends when the user types a message to Ogima
class ChatRequest(BaseModel):
    message: str

# What FastAPI returns back to Unity
class ChatResponse(BaseModel):
    reply: str