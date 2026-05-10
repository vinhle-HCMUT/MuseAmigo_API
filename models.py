from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Float, JSON, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)

    theme = Column(String(20), default="light") # e.g. "light" or "dark"
    language = Column(String(20), default="English") # e.g. "English", "Vietnamese"
    font_size = Column(String(20), default="Medium")
    scheme = Column(String(20), default="0xFFCC353A")
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(String(50), nullable=True)

    # superadmin | manager | visitor (mobile app users are visitor)
    role = Column(String(30), default="visitor", index=True)
    managed_museum_id = Column(Integer, ForeignKey("museums.id"), nullable=True)

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
    # Audio asset for artifact description
    audio_asset = Column(String(200), default="") # e.g., "assets/audio/artifact_001.mp3"
    # Links this artifact to a specific museum
    museum_id = Column(Integer, ForeignKey("museums.id"))

    # Normalized 0–1 position on the museum indoor map image; optional.
    map_x = Column(Float, nullable=True)
    map_y = Column(Float, nullable=True)
    floor_id = Column(
        Integer,
        ForeignKey("museum_floors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


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
    artifacts = Column(JSON) # List of artifact codes included in this exhibition, stored as a JSON string or comma-separated values

    map_x = Column(Float, nullable=True)
    map_y = Column(Float, nullable=True)
    floor_id = Column(
        Integer,
        ForeignKey("museum_floors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    museum_id = Column(Integer, ForeignKey("museums.id"))
    ticket_type = Column(String(50))
    amount = Column(Integer)
    status = Column(String(20), default="PENDING") # PENDING, PAID
    created_at = Column(String(50))
    paid_at = Column(String(50), nullable=True)  # YYYY-MM-DD when status became PAID

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))           # e.g., "Museum Highlights"
    estimated_time = Column(String(50))  # e.g., "45 min"
    stops_json = Column(Text, nullable=True)  # JSON array of stop labels/positions
    
    # Links this route to a specific museum
    museum_id = Column(Integer, ForeignKey("museums.id"))

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))           # e.g., "First Steps"
    description = Column(String(500))    # e.g., "Scan your first artifact"
    requirement_type = Column(String(50)) # e.g., "scan_count", "area_complete", "total_artifacts"
    requirement_value = Column(Integer)   # e.g., 1 for first scan, 20 for discover 20 artifacts
    points = Column(Integer, default=50)  # Points awarded for this achievement
    museum_id = Column(Integer, ForeignKey("museums.id"), nullable=True) # NULL for global achievements

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    museum_id = Column(Integer, ForeignKey("museums.id"), nullable=True) # Track which museum this was earned in
    is_completed = Column(Boolean, default=False)
    completed_at = Column(String(50), nullable=True) # Date when completed


class MuseumFloor(Base):
    """Indoor floor labels and order (editable in dashboard; mobile uses for chips)."""

    __tablename__ = "museum_floors"

    id = Column(Integer, primary_key=True, index=True)
    museum_id = Column(Integer, ForeignKey("museums.id"), nullable=False, index=True)
    label = Column(String(128), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    # Per-floor raster maps (normalized coords are relative to these images).
    indoor_map_2d_path = Column(String(500), nullable=True)
    indoor_map_3d_path = Column(String(500), nullable=True)


class MapDestination(Base):
    """POIs on the indoor map: WC, café, stairs, entrance, etc. (title, color, coords, floor)."""

    __tablename__ = "map_destinations"

    id = Column(Integer, primary_key=True, index=True)
    museum_id = Column(Integer, ForeignKey("museums.id"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False, default="other")
    marker_color = Column(String(32), nullable=False, default="#6366F1")
    map_x = Column(Float, nullable=False)
    map_y = Column(Float, nullable=False)
    floor_id = Column(
        Integer,
        ForeignKey("museum_floors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )