from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Float
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)

    theme = Column(String(20), default="light") # e.g., "light" or "dark"
    language = Column(String(20), default="en") # e.g., "en", "vi", or "ja"
    font_size = Column(Integer, default=14) # Font size in pixels

class Museum(Base):
    __tablename__ = "museums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    operating_hours = Column(String(50))
    base_ticket_price = Column(Integer)

    latitude = Column(Float)   # e.g., 10.7769 (Ho Chi Minh City)
    longitude = Column(Float)  # e.g., 106.6951

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    artifact_code = Column(String(50), unique=True, index=True) # This is what the QR code scans!
    title = Column(String(100))
    year = Column(String(50))
    description = Column(String(2000))
    is_3d_available = Column(Boolean, default=False)
    
    # Tell Unity which 3D file to load ---
    unity_prefab_name = Column(String(100)) # e.g., "Model_T54_Tank" or "Model_Bust_Statue"
    # Links this artifact to a specific museum
    museum_id = Column(Integer, ForeignKey("museums.id"))
class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    
    # These Foreign Keys link exactly to the IDs in your other tables
    user_id = Column(Integer, ForeignKey("users.id"))
    artifact_id = Column(Integer, ForeignKey("artifacts.id"))

class Exhibition(Base):
    __tablename__ = "exhibitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))        # e.g., "Exhibition of paintings"
    location = Column(String(100))    # e.g., "Hall C"
    
    # Links this exhibition to a specific museum
    museum_id = Column(Integer, ForeignKey("museums.id"))

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_type = Column(String(50))  # e.g., "Adult", "Student", "Children"
    purchase_date = Column(String(50)) 
    qr_code = Column(String(255), unique=True, index=True) # The code they scan at the entrance
    is_used = Column(Boolean, default=False)
    
    # Links the ticket to the specific user who bought it, and the museum it is for
    user_id = Column(Integer, ForeignKey("users.id"))
    museum_id = Column(Integer, ForeignKey("museums.id"))

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))           # e.g., "Museum Highlights"
    estimated_time = Column(String(50))  # e.g., "45 min"
    stops_count = Column(Integer)        # e.g., 4
    
    # Links this route to a specific museum
    museum_id = Column(Integer, ForeignKey("museums.id"))