import os
import base64
from pathlib import Path
import uuid # Dùng uuid để tên file không bao giờ bị trùng
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json
from generate_audio import audio_to_text, text_to_audio
import models, schemas
from indoor_map_helpers import (
    artifact_to_response,
    exhibition_to_response,
    ensure_floor_belongs_to_museum,
    resolve_floor_id_for_museum,
)
from dashboard_api import router as dashboard_router
from database import engine, get_db
from staff_auth import create_staff_token, effective_role
from datetime import date, datetime, timedelta
import secrets
from agent import agent_executor, get_ogima_response, system_message as ogima_system_message
from sqlalchemy.exc import IntegrityError

# Creates the tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development/testing
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Lấy đường dẫn thư mục hiện tại của source code
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"

# Tạo thư mục temp nếu chưa có
TEMP_DIR.mkdir(exist_ok=True)

# Static files (indoor map images). Place PNG/JPEG under static/maps/ and set paths on museums.
STATIC_ROOT = BASE_DIR / "static"
MAPS_DIR = STATIC_ROOT / "maps"
STATIC_ROOT.mkdir(exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)
_PLACEHOLDER_PNG = MAPS_DIR / "placeholder.png"
if not _PLACEHOLDER_PNG.exists():
    _PLACEHOLDER_PNG.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
    )
app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")


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


def seed_staff_users(db: Session) -> None:
    """Demo staff accounts for the admin dashboard (change passwords in production)."""
    staff_accounts = [
        {
            "email": "superadmin@museamigo.com",
            "full_name": "Super Admin",
            "password": "admin123",
            "role": "superadmin",
            "managed_museum_id": None,
        },
        {
            "email": "manager.ip@museamigo.com",
            "full_name": "Independence Palace Manager",
            "password": "manager123",
            "role": "manager",
            "managed_museum_id": 1,
        },
        {
            "email": "manager.wrm@museamigo.com",
            "full_name": "War Remnants Manager",
            "password": "manager123",
            "role": "manager",
            "managed_museum_id": 2,
        },
    ]
    for item in staff_accounts:
        u = db.query(models.User).filter(models.User.email == item["email"]).first()
        if u:
            u.role = item["role"]
            u.managed_museum_id = item["managed_museum_id"]
            u.hashed_password = item["password"]
            if not u.full_name:
                u.full_name = item["full_name"]
        else:
            db.add(
                models.User(
                    full_name=item["full_name"],
                    email=item["email"],
                    hashed_password=item["password"],
                    role=item["role"],
                    managed_museum_id=item["managed_museum_id"],
                )
            )
    db.commit()


# Indoor map positions (normalized 0–1) copied from Flutter museum_3d_map_screen.dart hardcoded map.
ARTIFACT_MAP_COORDS: dict[str, tuple[float, float, str]] = {
    "IP-001": (0.16, 0.2, "Floor 1"),
    "IP-002": (0.29, 0.18, "Floor 1"),
    "IP-003": (0.24, 0.55, "Floor 1"),
    "IP-004": (0.68, 0.5, "Floor 1"),
    "IP-005": (0.26, 0.3, "Floor 2"),
    "IP-006": (0.33, 0.3, "Floor 1"),
    "IP-007": (0.21, 0.34, "Floor 1"),
    "IP-008": (0.18, 0.5, "Floor 1"),
    "IP-009": (0.67, 0.2, "Floor 1"),
    "IP-010": (0.29, 0.64, "Floor 1"),
    "IP-011": (0.36, 0.42, "Floor 2"),
    "IP-012": (0.8, 0.63, "Floor 1"),
    "IP-013": (0.73, 0.34, "Floor 1"),
    "IP-014": (0.74, 0.3, "Floor 2"),
    "IP-015": (0.79, 0.18, "Floor 1"),
    "WRM-001": (0.62, 0.28, "Floor 1"),
    "WRM-002": (0.78, 0.56, "Floor 1"),
    "FAM-001": (0.58, 0.34, "Floor 1"),
    "FAM-002": (0.6, 0.36, "Floor 2"),
    "HCM-001": (0.62, 0.34, "Floor 1"),
    "HCM-002": (0.62, 0.38, "Floor 2"),
}


def apply_artifact_map_coordinates(db: Session) -> None:
    """Sync map_x / map_y / floor_id from ARTIFACT_MAP_COORDS for seeded artifacts."""
    for code, (x, y, floor_label) in ARTIFACT_MAP_COORDS.items():
        art = (
            db.query(models.Artifact)
            .filter(models.Artifact.artifact_code == code)
            .first()
        )
        if art:
            art.map_x = x
            art.map_y = y
            art.floor_id = resolve_floor_id_for_museum(
                db, art.museum_id, floor_label
            )
    db.commit()


def seed_artifacts(db: Session) -> None:
    seed_data = [
        # Independence Palace Artifacts
        {
            "artifact_code": "IP-001",
            "title": "Tank 390",
            "year": "1975",
            "description": "Tank 390 displayed in the Fall of Saigon exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
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
        {
            "artifact_code": "IP-004",
            "title": "Mercedes-Benz 200 W110",
            "year": "1960s",
            "description": "Presidential lifestyle exhibition vehicle.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-005",
            "title": "War Command Bunker Map",
            "year": "1975",
            "description": "War Command Bunker exhibition map.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-006",
            "title": "F-5E Bombing Marks",
            "year": "1975",
            "description": "Fall of Saigon exhibition — F-5E bombing marks.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-007",
            "title": "Jeep M151A2",
            "year": "1975",
            "description": "Fall of Saigon exhibition — Jeep M151A2.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-008",
            "title": "Binh Ngo Dai Cao Lacquer Painting",
            "year": "15th century",
            "description": "Diplomacy & State Ceremony exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-009",
            "title": "Cabinet Room Table",
            "year": "1960s",
            "description": "Presidential Power & Governance exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-010",
            "title": "The Golden Dragon Tapestry",
            "year": "1960s",
            "description": "Diplomacy & State Ceremony exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-011",
            "title": "Telecommunications Center",
            "year": "1975",
            "description": "War Command Bunker exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-012",
            "title": "The Presidential Bed",
            "year": "1960s",
            "description": "Presidential Lifestyle exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-013",
            "title": "National Security Council Maps",
            "year": "1970s",
            "description": "Presidential Power & Governance exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-014",
            "title": "Basement Cinema Projector",
            "year": "1975",
            "description": "Air Warfare & Evacuation exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
        },
        {
            "artifact_code": "IP-015",
            "title": "Vice President's Desk",
            "year": "1960s",
            "description": "Presidential Power & Governance exhibition.",
            "is_3d_available": False,
            "unity_prefab_name": "",
            "audio_asset": "",
            "museum_id": 1,
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
            "museum_id": 1,
            "artifacts": ["IP-011", "IP-014", "IP-005"],
            "map_x": 0.35,
            "map_y": 0.36,
            "floor_label": "Floor 2",
        },
        {
            "name": "War History Gallery",
            "location": "Ground Floor - East Wing",
            "museum_id": 1,
            "artifacts": ["IP-001", "IP-002", "IP-006", "IP-007"],
            "map_x": 0.25,
            "map_y": 0.26,
            "floor_label": "Floor 1",
        },
        {
            "name": "Diplomatic Reception Hall",
            "location": "1st Floor - Central Hall",
            "museum_id": 1,
            "artifacts": ["IP-003", "IP-008", "IP-010"],
            "map_x": 0.24,
            "map_y": 0.58,
            "floor_label": "Floor 1",
        },
        # War Remnants Museum Exhibitions
        {
            "name": "War Crimes Exhibition",
            "location": "Building A - Upper Floor",
            "museum_id": 2,
            "artifacts": ["WRM-001", "WRM-002"],
            "map_x": 0.22,
            "map_y": 0.22,
            "floor_label": "Floor 1",
        },
        {
            "name": "International Support Gallery",
            "location": "Building B - Main Hall",
            "museum_id": 2,
            "artifacts": ["WRM-001"],
            "map_x": 0.2,
            "map_y": 0.22,
            "floor_label": "Floor 2",
        },
        {
            "name": "Peace and Reconciliation Display",
            "location": "Outdoor Exhibition Area",
            "museum_id": 2,
            "artifacts": ["WRM-002"],
            "map_x": 0.62,
            "map_y": 0.34,
            "floor_label": "Floor 2",
        },
        # Fine Arts Museum Exhibitions
        {
            "name": "Contemporary Vietnamese Art",
            "location": "Main Gallery - 1st Floor",
            "museum_id": 3,
            "artifacts": ["FAM-001"],
            "map_x": 0.2,
            "map_y": 0.24,
            "floor_label": "Floor 1",
        },
        {
            "name": "Traditional Crafts Exhibition",
            "location": "Heritage Wing - 2nd Floor",
            "museum_id": 3,
            "artifacts": ["FAM-002"],
            "map_x": 0.2,
            "map_y": 0.22,
            "floor_label": "Floor 2",
        },
        {
            "name": "International Art Collection",
            "location": "International Gallery - Ground Floor",
            "museum_id": 3,
            "artifacts": ["FAM-001", "FAM-002"],
            "map_x": 0.8,
            "map_y": 0.56,
            "floor_label": "Floor 2",
        },
        # HCMC Museum Exhibitions
        {
            "name": "Saigon History Timeline",
            "location": "Main Hall - Ground Floor",
            "museum_id": 4,
            "artifacts": ["HCM-001"],
            "map_x": 0.22,
            "map_y": 0.24,
            "floor_label": "Floor 1",
        },
        {
            "name": "Traditional Culture Display",
            "location": "Cultural Wing - 2nd Floor",
            "museum_id": 4,
            "artifacts": ["HCM-002"],
            "map_x": 0.22,
            "map_y": 0.22,
            "floor_label": "Floor 2",
        },
        {
            "name": "Urban Development Exhibition",
            "location": "Modern History Section - 1st Floor",
            "museum_id": 4,
            "artifacts": ["HCM-001", "HCM-002"],
            "map_x": 0.78,
            "map_y": 0.56,
            "floor_label": "Floor 2",
        },
    ]

    for item in seed_data:
        floor_id = resolve_floor_id_for_museum(
            db, item["museum_id"], item.get("floor_label")
        )
        existing = db.query(models.Exhibition).filter(
            models.Exhibition.museum_id == item["museum_id"],
            models.Exhibition.name == item["name"]
        ).first()
        row = {
            "name": item["name"],
            "location": item["location"],
            "museum_id": item["museum_id"],
            "artifacts": item["artifacts"],
            "map_x": item["map_x"],
            "map_y": item["map_y"],
            "floor_id": floor_id,
        }
        if existing:
            existing.location = row["location"]
            existing.artifacts = row["artifacts"]
            existing.map_x = row["map_x"]
            existing.map_y = row["map_y"]
            existing.floor_id = row["floor_id"]
        else:
            db.add(models.Exhibition(**row))

    db.commit()


def ensure_default_museum_floors(db: Session) -> None:
    """Create default floor rows when a museum has none (before artifact/exhibition map anchors)."""
    for m in db.query(models.Museum).order_by(models.Museum.id).all():
        n_floors = (
            db.query(models.MuseumFloor)
            .filter(models.MuseumFloor.museum_id == m.id)
            .count()
        )
        if n_floors == 0:
            db.add(
                models.MuseumFloor(
                    museum_id=m.id, label="Floor 1", sort_order=0
                )
            )
            db.add(
                models.MuseumFloor(
                    museum_id=m.id, label="Floor 2", sort_order=1
                )
            )
    db.commit()


def seed_default_map_destinations_museum1(db: Session) -> None:
    """Sample map POIs for museum 1 (WC, café, stairs); requires floors."""
    if (
        db.query(models.MapDestination)
        .filter(models.MapDestination.museum_id == 1)
        .count()
        > 0
    ):
        return
    f1 = (
        db.query(models.MuseumFloor)
        .filter(
            models.MuseumFloor.museum_id == 1,
            models.MuseumFloor.label == "Floor 1",
        )
        .first()
    )
    f2 = (
        db.query(models.MuseumFloor)
        .filter(
            models.MuseumFloor.museum_id == 1,
            models.MuseumFloor.label == "Floor 2",
        )
        .first()
    )
    if f1:
        db.add(
            models.MapDestination(
                museum_id=1,
                title="Restroom",
                category="restroom",
                marker_color="#F59E0B",
                map_x=0.12,
                map_y=0.55,
                floor_id=f1.id,
            )
        )
        db.add(
            models.MapDestination(
                museum_id=1,
                title="Café",
                category="cafe",
                marker_color="#8B5E3C",
                map_x=0.88,
                map_y=0.22,
                floor_id=f1.id,
            )
        )
        db.add(
            models.MapDestination(
                museum_id=1,
                title="Stairs to Floor 2",
                category="stairs",
                marker_color="#60A5FA",
                map_x=0.5,
                map_y=0.08,
                floor_id=f1.id,
            )
        )
    if f2:
        db.add(
            models.MapDestination(
                museum_id=1,
                title="Stairs to Floor 1",
                category="stairs",
                marker_color="#60A5FA",
                map_x=0.48,
                map_y=0.92,
                floor_id=f2.id,
            )
        )
    db.commit()


def seed_routes(db: Session) -> None:
    seed_data = [
        # Independence Palace Routes
        {
            "name": "Presidential Tour",
            "estimated_time": "45 min",
            "museum_id": 1
        },
        {
            "name": "Historical Highlights",
            "estimated_time": "30 min",
            "museum_id": 1
        },
        {
            "name": "Architecture Tour",
            "estimated_time": "60 min",
            "museum_id": 1
        },
        # War Remnants Museum Routes
        {
            "name": "War History Path",
            "estimated_time": "90 min",
            "museum_id": 2
        },
        {
            "name": "Quick Overview",
            "estimated_time": "30 min",
            "museum_id": 2
        },
        {
            "name": "Photography Tour",
            "estimated_time": "45 min",
            "museum_id": 2
        },
        # Fine Arts Museum Routes
        {
            "name": "Masterpieces Collection",
            "estimated_time": "60 min",
            "museum_id": 3
        },
        {
            "name": "Traditional Arts Walk",
            "estimated_time": "40 min",
            "museum_id": 3
        },
        # HCMC Museum Routes
        {
            "name": "City History Journey",
            "estimated_time": "75 min",
            "museum_id": 4
        },
        {
            "name": "Cultural Heritage Trail",
            "estimated_time": "50 min",
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
        else:
            db.add(models.Route(**item))

    db.commit()

def seed_achievements(db: Session) -> None:
    # 15 scan-count achievement templates shared across all museums
    achievement_templates = [
        ("First Steps", "Scan 1 artifact", 1, 50),
        ("Curious Visitor", "Scan 2 artifacts", 2, 100),
        ("Growing Collection", "Scan 3 artifacts", 3, 150),
        ("Dedicated Explorer", "Scan 5 artifacts", 5, 200),
        ("Museum Regular", "Scan 7 artifacts", 7, 250),
        ("History Buff", "Scan 10 artifacts", 10, 300),
        ("Avid Collector", "Scan 15 artifacts", 15, 350),
        ("Master Collector", "Scan 20 artifacts", 20, 400),
        ("Legendary Explorer", "Scan 30 artifacts", 30, 500),
        ("Ultimate Curator", "Scan 50 artifacts", 50, 600),
        ("Century Scans", "Scan 75 artifacts", 75, 700),
        ("Millennium Marks", "Scan 100 artifacts", 100, 800),
        ("Unstoppable", "Scan 150 artifacts", 150, 900),
        ("Museum Legend", "Scan 200 artifacts", 200, 1000),
        ("Infinite Explorer", "Scan 500 artifacts", 500, 1500),
    ]

    museums = db.query(models.Museum).all()

    for museum in museums:
        for name, description, requirement_value, points in achievement_templates:
            existing = db.query(models.Achievement).filter(
                models.Achievement.name == name,
                models.Achievement.museum_id == museum.id
            ).first()
            item = {
                "name": name,
                "description": description,
                "requirement_type": "museum_scan_count",
                "requirement_value": requirement_value,
                "points": points,
                "museum_id": museum.id
            }
            if existing:
                existing.description = description
                existing.requirement_type = "museum_scan_count"
                existing.requirement_value = requirement_value
                existing.points = points
            else:
                db.add(models.Achievement(**item))

    # Remove old global/per-museum achievements that are no longer in the template
    valid_names = {t[0] for t in achievement_templates}
    old_achievements = db.query(models.Achievement).filter(
        ~models.Achievement.name.in_(valid_names)
    ).all()
    for old in old_achievements:
        # Delete referencing user achievements first to avoid FK constraint errors
        db.query(models.UserAchievement).filter(
            models.UserAchievement.achievement_id == old.id
        ).delete(synchronize_session=False)
        db.delete(old)

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
    db.close()


def migrate_add_user_reset_columns():
    """Add reset_token and reset_token_expires columns to users table if they don't exist"""
    db = next(get_db())
    try:
        db.execute(text("""
            ALTER TABLE users ADD COLUMN reset_token VARCHAR(255) NULL
        """))
        db.commit()
        print("✓ Added reset_token column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ reset_token column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()

    try:
        db.execute(text("""
            ALTER TABLE users ADD COLUMN reset_token_expires VARCHAR(50) NULL
        """))
        db.commit()
        print("✓ Added reset_token_expires column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ reset_token_expires column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()
    db.close()


def migrate_add_user_settings_columns():
    """Add font_size and scheme columns to users table if they don't exist"""
    db = next(get_db())
    try:
        db.execute(text("""
            ALTER TABLE users ADD COLUMN font_size VARCHAR(20) DEFAULT 'Medium'
        """))
        db.commit()
        print("✓ Added font_size column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ font_size column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()

    try:
        db.execute(text("""
            ALTER TABLE users ADD COLUMN scheme VARCHAR(20) DEFAULT '0xFFCC353A'
        """))
        db.commit()
        print("✓ Added scheme column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ scheme column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()
    finally:
        db.close()

def migrate_add_user_staff_columns():
    """Add role and managed_museum_id to users for staff dashboard."""
    db = next(get_db())
    try:
        db.execute(
            text("""
            ALTER TABLE users ADD COLUMN role VARCHAR(30) DEFAULT 'visitor'
        """)
        )
        db.commit()
        print("✓ Added role column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ role column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()

    try:
        db.execute(
            text("""
            ALTER TABLE users ADD COLUMN managed_museum_id INTEGER NULL
        """)
        )
        db.commit()
        print("✓ Added managed_museum_id column to users table")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("✓ managed_museum_id column already exists")
        else:
            print(f"⚠ Migration note: {e}")
        db.rollback()
    finally:
        db.close()


def migrate_normalize_user_roles():
    """Map legacy roles to superadmin | manager | visitor."""
    db = next(get_db())
    try:
        db.execute(
            text("""
            UPDATE users SET role = 'visitor'
            WHERE role IS NULL OR TRIM(role) = '' OR LOWER(role) = 'user'
        """)
        )
        db.execute(
            text("""
            UPDATE users SET role = 'manager' WHERE role = 'museum_manager'
        """)
        )
        db.commit()
        print("✓ Normalized user roles (visitor / manager / superadmin)")
    except Exception as e:
        print(f"⚠ Role normalization note: {e}")
        db.rollback()
    finally:
        db.close()


def migrate_create_orders_table():
    """Create orders table if it doesn't exist"""
    db = next(get_db())
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                museum_id INTEGER,
                ticket_type VARCHAR(50),
                amount INTEGER,
                status VARCHAR(20) DEFAULT 'PENDING',
                created_at VARCHAR(50),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(museum_id) REFERENCES museums(id)
            )
        """))
        db.commit()
        print("✓ Created orders table if not exists")
    except Exception as e:
        print(f"⚠ Migration note for orders table: {e}")
        db.rollback()
    finally:
        db.close()


def migrate_fix_superadmin_role_typo():
    """Legacy seed stored email in `role`; column may be VARCHAR(20) — too short."""
    db = next(get_db())
    try:
        db.execute(
            text(
                "UPDATE users SET role = 'superadmin' "
                "WHERE role = 'superadmin@museamigo.com' "
                "OR (role LIKE '%@%' AND email = 'superadmin@museamigo.com')"
            )
        )
        db.commit()
        print("✓ Normalized superadmin role (email no longer stored in role)")
    except Exception as e:
        db.rollback()
        print(f"⚠ migrate_fix_superadmin_role_typo: {e}")
    finally:
        db.close()


def migrate_add_ticket_is_used_column():
    """Ensure tickets.is_used exists (older SQLite DBs may lack it)."""
    db = next(get_db())
    try:
        db.execute(
            text("ALTER TABLE tickets ADD COLUMN is_used BOOLEAN DEFAULT 0")
        )
        db.commit()
        print("✓ Added column tickets.is_used")
    except Exception as e:
        db.rollback()
        err = str(e).lower()
        if "duplicate column" in err or "already exists" in err:
            print("✓ tickets.is_used column already exists")
        else:
            print(f"⚠ tickets.is_used migration note: {e}")
    finally:
        db.close()


def migrate_add_order_paid_at_column():
    """Add paid_at for revenue date filtering; backfill from created_at for PAID rows."""
    db = next(get_db())
    try:
        db.execute(text("ALTER TABLE orders ADD COLUMN paid_at VARCHAR(50)"))
        db.commit()
        print("✓ Added column orders.paid_at")
    except Exception as e:
        db.rollback()
        err = str(e).lower()
        if "duplicate column" not in err and "already exists" not in err:
            print(f"⚠ orders.paid_at add column: {e}")
    try:
        db.execute(
            text(
                "UPDATE orders SET paid_at = created_at WHERE status = 'PAID' "
                "AND (paid_at IS NULL OR paid_at = '')"
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠ orders.paid_at backfill: {e}")
    finally:
        db.close()


def migrate_drop_museum_indoor_map_columns() -> None:
    """Drop legacy museum-level indoor map path columns (use museum_floors instead)."""
    db = next(get_db())
    for col in ("indoor_map_2d_path", "indoor_map_3d_path"):
        try:
            db.execute(text(f"ALTER TABLE museums DROP COLUMN {col}"))
            db.commit()
            print(f"✓ Dropped museums.{col}")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if (
                "unknown column" in err
                or "doesn't exist" in err
                or "check that column/key exists" in err
            ):
                print(f"✓ museums.{col} already dropped")
            else:
                print(f"⚠ drop museums.{col}: {e}")
    db.close()


def migrate_artifact_map_coordinate_columns():
    """Add normalized map overlay coordinates to artifacts."""
    db = next(get_db())
    for stmt, label in (
        ("ALTER TABLE artifacts ADD COLUMN map_x FLOAT NULL", "map_x"),
        ("ALTER TABLE artifacts ADD COLUMN map_y FLOAT NULL", "map_y"),
    ):
        try:
            db.execute(text(stmt))
            db.commit()
            print(f"✓ Added artifacts.{label}")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                print(f"✓ artifacts.{label} already exists")
            else:
                print(f"⚠ artifacts.{label} migration: {e}")
    db.close()


def migrate_exhibition_map_columns():
    """Add optional indoor map anchor for exhibitions."""
    db = next(get_db())
    for stmt, label in (
        ("ALTER TABLE exhibitions ADD COLUMN map_x FLOAT NULL", "map_x"),
        ("ALTER TABLE exhibitions ADD COLUMN map_y FLOAT NULL", "map_y"),
    ):
        try:
            db.execute(text(stmt))
            db.commit()
            print(f"✓ Added exhibitions.{label}")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                print(f"✓ exhibitions.{label} already exists")
            else:
                print(f"⚠ exhibitions.{label} migration: {e}")
    db.close()


def migrate_museum_floor_indoor_map_paths() -> None:
    """Add per-floor 2D/3D indoor map image paths."""
    db = next(get_db())
    for stmt, label in (
        (
            "ALTER TABLE museum_floors ADD COLUMN indoor_map_2d_path VARCHAR(500) NULL",
            "indoor_map_2d_path",
        ),
        (
            "ALTER TABLE museum_floors ADD COLUMN indoor_map_3d_path VARCHAR(500) NULL",
            "indoor_map_3d_path",
        ),
    ):
        try:
            db.execute(text(stmt))
            db.commit()
            print(f"✓ Added museum_floors.{label}")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print(f"✓ museum_floors.{label} already exists")
            else:
                print(f"⚠ museum_floors.{label} migration: {e}")
    db.close()


def migrate_route_stops_json_column() -> None:
    """Store explicit route stop labels/positions as JSON text."""
    db = next(get_db())
    try:
        db.execute(text("ALTER TABLE routes ADD COLUMN stops_json TEXT NULL"))
        db.commit()
        print("✓ Added routes.stops_json")
    except Exception as e:
        db.rollback()
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err:
            print("✓ routes.stops_json already exists")
        else:
            print(f"⚠ routes.stops_json migration: {e}")
    finally:
        db.close()


def migrate_drop_route_stops_count_column() -> None:
    """Remove legacy routes.stops_count (count is derived from stops_json)."""
    db = next(get_db())
    try:
        db.execute(text("ALTER TABLE routes DROP COLUMN stops_count"))
        db.commit()
        print("✓ Dropped routes.stops_count")
    except Exception as e:
        db.rollback()
        err = str(e).lower()
        if (
            "unknown column" in err
            or "doesn't exist" in err
            or "check that column/key exists" in err
        ):
            print("✓ routes.stops_count already dropped")
        else:
            print(f"⚠ drop routes.stops_count: {e}")
    finally:
        db.close()


def migrate_artifact_exhibition_floor_id_columns() -> None:
    """Add floor_id FK to museum_floors for artifacts and exhibitions."""
    db = next(get_db())
    specs = (
        ("artifacts", "fk_artifacts_museum_floor"),
        ("exhibitions", "fk_exhibitions_museum_floor"),
    )
    for table, fk_name in specs:
        try:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN floor_id INT NULL"))
            db.commit()
            print(f"✓ Added {table}.floor_id")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print(f"✓ {table}.floor_id already exists")
            else:
                print(f"⚠ {table}.floor_id add: {e}")
        try:
            db.execute(
                text(
                    f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY (floor_id) REFERENCES museum_floors(id) ON DELETE SET NULL"
                )
            )
            db.commit()
            print(f"✓ Added {table} floor_id foreign key")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if (
                "duplicate" in err
                or "already exists" in err
                or "errno 1826" in err
            ):
                print(f"✓ {table} floor_id FK already exists")
            else:
                print(f"⚠ {table} floor_id FK: {e}")
    db.close()


def backfill_floor_id_from_legacy_map_floor_columns(db: Session) -> None:
    """One-time: set floor_id from legacy map_floor label (before column drop)."""
    try:
        db.execute(
            text(
                "UPDATE artifacts a "
                "INNER JOIN museum_floors mf ON mf.museum_id = a.museum_id "
                "AND mf.label = a.map_floor "
                "SET a.floor_id = mf.id "
                "WHERE a.map_floor IS NOT NULL AND a.map_floor != ''"
            )
        )
        db.execute(
            text(
                "UPDATE exhibitions e "
                "INNER JOIN museum_floors mf ON mf.museum_id = e.museum_id "
                "AND mf.label = e.map_floor "
                "SET e.floor_id = mf.id "
                "WHERE e.map_floor IS NOT NULL AND e.map_floor != ''"
            )
        )
        db.commit()
        print("✓ Backfilled floor_id from legacy map_floor")
    except Exception as e:
        db.rollback()
        err = str(e).lower()
        if "unknown column" in err and "map_floor" in err:
            print("✓ No legacy map_floor columns; skipped floor_id backfill")
        else:
            print(f"⚠ floor_id backfill: {e}")


def migrate_drop_legacy_map_floor_columns() -> None:
    """Remove map_floor after floor_id migration."""
    db = next(get_db())
    for table in ("artifacts", "exhibitions"):
        try:
            db.execute(text(f"ALTER TABLE {table} DROP COLUMN map_floor"))
            db.commit()
            print(f"✓ Dropped {table}.map_floor")
        except Exception as e:
            db.rollback()
            err = str(e).lower()
            if (
                "unknown column" in err
                or "doesn't exist" in err
                or "check that column/key exists" in err
            ):
                print(f"✓ {table}.map_floor already dropped")
            else:
                print(f"⚠ drop {table}.map_floor: {e}")
    db.close()


@app.on_event("startup")
def startup_seed_data():
    try:
        # Run migrations first to ensure schema is up-to-date
        print("Running migration: audio_asset column...")
        migrate_add_audio_asset_column()
        print("Running migration: user reset columns...")
        migrate_add_user_reset_columns()
        print("Running migration: user settings columns...")
        migrate_add_user_settings_columns()
        print("Running migration: orders table...")
        migrate_create_orders_table()
        print("Running migration: orders.paid_at column...")
        migrate_add_order_paid_at_column()
        print("Running migration: tickets.is_used column...")
        migrate_add_ticket_is_used_column()
        print("Running migration: fix superadmin role typo...")
        migrate_fix_superadmin_role_typo()
        print("Running migration: user staff columns...")
        migrate_add_user_staff_columns()
        print("Running migration: normalize user roles...")
        migrate_normalize_user_roles()
        print("Running migration: drop legacy museum indoor map columns...")
        migrate_drop_museum_indoor_map_columns()
        print("Running migration: artifact map coordinate columns...")
        migrate_artifact_map_coordinate_columns()
        print("Running migration: exhibition map columns...")
        migrate_exhibition_map_columns()
        print("Running migration: artifact & exhibition floor_id...")
        migrate_artifact_exhibition_floor_id_columns()
        print("Running migration: museum_floors indoor map paths...")
        migrate_museum_floor_indoor_map_paths()
        print("Running migration: route stops json...")
        migrate_route_stops_json_column()
        print("Running migration: drop legacy route stops_count...")
        migrate_drop_route_stops_count_column()

        print("Opening DB session for seeding...")
        db = next(get_db())
        try:
            print("Seeding museums...")
            seed_museums(db)
            print("Seeding staff users...")
            seed_staff_users(db)
            print("Seeding artifacts...")
            seed_artifacts(db)
            print("Ensuring default museum floors...")
            ensure_default_museum_floors(db)
            print("Backfilling floor_id from legacy map_floor (if present)...")
            backfill_floor_id_from_legacy_map_floor_columns(db)
            print("Applying artifact indoor map coordinates...")
            apply_artifact_map_coordinates(db)
            print("Seeding exhibitions...")
            seed_exhibitions(db)
            print("Seeding default map destination POIs...")
            seed_default_map_destinations_museum1(db)
            print("Seeding routes...")
            seed_routes(db)
            print("Seeding achievements...")
            seed_achievements(db)
            print("Cleaning up artifact id 1...")
            _delete_artifact_id_one(db)
            print("Startup seeding complete.")
        finally:
            db.close()
        print("Running migration: drop legacy map_floor columns...")
        migrate_drop_legacy_map_floor_columns()
    except Exception as e:
        print(f"ERROR during startup: {e}")
        import traceback
        traceback.print_exc()
        # Don't re-raise — let the app start even if seeding fails


def _delete_artifact_id_one(db: Session) -> None:
    artifact = db.query(models.Artifact).filter(models.Artifact.id == 1).first()
    if artifact:
        # Delete associated collections first to avoid FK constraint issues
        db.query(models.Collection).filter(models.Collection.artifact_id == 1).delete(synchronize_session=False)
        db.delete(artifact)
        db.commit()


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
    db_user = models.User(
        full_name=user.full_name.strip(),
        email=user.email.strip(),
        hashed_password=user.password,
        role="visitor",
    )

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
        "full_name": db_user.full_name,
        "theme": db_user.theme,
        "language": db_user.language,
        "font_size": db_user.font_size,
        "scheme": db_user.scheme
    }


@app.post("/auth/staff-login", response_model=schemas.StaffLoginResponse)
def staff_login(credentials: schemas.StaffLoginRequest, db: Session = Depends(get_db)):
    if not credentials.email or not credentials.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not credentials.password or not credentials.password.strip():
        raise HTTPException(status_code=400, detail="Password is required")

    db_user = (
        db.query(models.User)
        .filter(models.User.email == credentials.email.strip())
        .first()
    )
    if not db_user or db_user.hashed_password != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    er = effective_role(db_user)
    if er not in ("superadmin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not authorized for the staff dashboard",
        )
    if er == "manager" and not db_user.managed_museum_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager is not assigned to a museum",
        )

    token = create_staff_token(db_user.id, er, db_user.managed_museum_id)
    user_payload = schemas.StaffMeResponse(
        id=db_user.id,
        full_name=db_user.full_name or "",
        email=db_user.email or "",
        role=er,
        managed_museum_id=db_user.managed_museum_id,
    )
    return schemas.StaffLoginResponse(access_token=token, user=user_payload)


@app.post("/auth/forgot-password")
def forgot_password(data: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == data.email.strip()).first()
    if not db_user:
        # Return success even if email not found to prevent email enumeration
        return {"message": "If the email exists, a reset token has been generated."}

    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    db_user.reset_token = token
    db_user.reset_token_expires = expires
    db.commit()

    # In production, send email here. For demo, return token in response.
    return {
        "message": "Password reset token generated.",
        "token": token,
        "expires": expires
    }

@app.post("/auth/reset-password")
def reset_password(data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.reset_token == data.token.strip()).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    if not db_user.reset_token_expires:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    try:
        expires = datetime.fromisoformat(db_user.reset_token_expires)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    if datetime.utcnow() > expires:
        raise HTTPException(status_code=400, detail="Token has expired.")

    if not data.new_password or len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    db_user.hashed_password = data.new_password
    db_user.reset_token = None
    db_user.reset_token_expires = None
    db.commit()

    return {"message": "Password has been reset successfully."}

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": db_user.id,
        "full_name": db_user.full_name,
        "email": db_user.email,
        "theme": db_user.theme,
        "language": db_user.language,
        "font_size": db_user.font_size,
        "scheme": db_user.scheme
    }

@app.patch("/users/{user_id}")
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        data.full_name = data.full_name.strip()
        if not data.full_name:
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        db_user.full_name = data.full_name
        db.commit()
        db.refresh(db_user)

    return {
        "id": db_user.id,
        "full_name": db_user.full_name,
        "email": db_user.email,
    }

# --- Admin endpoints for full user management ---

@app.get("/admin/users", response_model=list[schemas.UserResponse])
def admin_get_all_users(db: Session = Depends(get_db)):
    """Return list of all users (admin view)."""
    return db.query(models.User).all()

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user and cascade related data (admin)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete related collections, achievements, tickets, orders first to avoid FK issues
    db.query(models.Collection).filter(models.Collection.user_id == user_id).delete(synchronize_session=False)
    db.query(models.UserAchievement).filter(models.UserAchievement.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Ticket).filter(models.Ticket.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Order).filter(models.Order.user_id == user_id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"message": f"User {user_id} deleted"}

@app.put("/admin/users/{user_id}", response_model=schemas.UserResponse)
def admin_update_user(user_id: int, data: schemas.AdminUserUpdate, db: Session = Depends(get_db)):
    """Admin can update any user fields."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.email is not None:
        user.email = data.email.strip()
    if data.theme is not None:
        user.theme = data.theme
    if data.language is not None:
        user.language = data.language
    if data.font_size is not None:
        user.font_size = data.font_size
    if data.scheme is not None:
        user.scheme = data.scheme

    db.commit()
    db.refresh(user)
    return user

# 1. Endpoint to load the Map/Discovery screen
@app.get("/museums", response_model=list[schemas.MuseumResponse])
def get_all_museums(db: Session = Depends(get_db)):
    museums = db.query(models.Museum).all()
    return museums


@app.get(
    "/museums/{museum_id}/indoor-map",
    response_model=schemas.IndoorMapPublicResponse,
)
def get_indoor_map(museum_id: int, db: Session = Depends(get_db)):
    """Legacy fallback endpoint: return first available per-floor map paths."""
    m = db.query(models.Museum).filter(models.Museum.id == museum_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Museum not found")
    p2: str | None = None
    p3: str | None = None
    floors = (
        db.query(models.MuseumFloor)
        .filter(models.MuseumFloor.museum_id == museum_id)
        .order_by(models.MuseumFloor.sort_order, models.MuseumFloor.id)
        .all()
    )
    for fl in floors:
        cand2 = (fl.indoor_map_2d_path or "").strip() or None
        cand3 = (fl.indoor_map_3d_path or "").strip() or None
        if p2 is None and cand2 is not None:
            p2 = cand2
        if p3 is None and cand3 is not None:
            p3 = cand3
        if p2 is not None and p3 is not None:
            break
    return schemas.IndoorMapPublicResponse(
        museum_id=museum_id, map_2d_path=p2, map_3d_path=p3
    )


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
            detail=f"Artifact code '{artifact_code}' not found. Available codes: IP-002, IP-003, WRM-001, WRM-002, FAM-001, FAM-002, HCM-001, HCM-002"
        )

    return artifact_to_response(artifact, db)

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
    return [exhibition_to_response(e, db) for e in exhibitions]

@app.get("/museums/{museum_id}/artifacts", response_model=list[schemas.ArtifactResponse])
def get_museum_artifacts(museum_id: int, db: Session = Depends(get_db)):
    artifacts = db.query(models.Artifact).filter(models.Artifact.museum_id == museum_id).all()
    return [artifact_to_response(a, db) for a in artifacts]


def _map_destination_public(
    row: models.MapDestination, db: Session
) -> schemas.MapDestinationResponse:
    fl = (
        db.query(models.MuseumFloor)
        .filter(models.MuseumFloor.id == row.floor_id)
        .first()
    )
    return schemas.MapDestinationResponse(
        id=row.id,
        museum_id=row.museum_id,
        title=row.title,
        category=row.category or "other",
        marker_color=row.marker_color or "#6366F1",
        map_x=row.map_x,
        map_y=row.map_y,
        floor_id=row.floor_id,
        floor_label=(fl.label if fl else ""),
    )


@app.get(
    "/museums/{museum_id}/floors",
    response_model=list[schemas.MuseumFloorResponse],
)
def get_museum_floors_public(museum_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Museum).filter(models.Museum.id == museum_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Museum not found")
    return (
        db.query(models.MuseumFloor)
        .filter(models.MuseumFloor.museum_id == museum_id)
        .order_by(models.MuseumFloor.sort_order, models.MuseumFloor.id)
        .all()
    )


@app.get(
    "/museums/{museum_id}/map-destinations",
    response_model=list[schemas.MapDestinationResponse],
)
def get_map_destinations_public(museum_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Museum).filter(models.Museum.id == museum_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Museum not found")
    rows = (
        db.query(models.MapDestination)
        .filter(models.MapDestination.museum_id == museum_id)
        .order_by(models.MapDestination.id)
        .all()
    )
    return [_map_destination_public(r, db) for r in rows]


@app.patch(
    "/artifacts/{artifact_id}/map-position",
    response_model=schemas.ArtifactResponse,
)
def patch_artifact_map_position(
    artifact_id: int,
    data: schemas.ArtifactMapPositionUpdate,
    db: Session = Depends(get_db),
):
    """Create/update/clear artifact position on the indoor map (normalized x,y in 0–1)."""
    art = db.query(models.Artifact).filter(models.Artifact.id == artifact_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    payload = data.model_dump(exclude_unset=True)
    if "floor_id" in payload:
        fid = payload["floor_id"]
        if fid is not None:
            ensure_floor_belongs_to_museum(db, art.museum_id, fid)
        art.floor_id = fid
    for key in ("map_x", "map_y"):
        if key in payload:
            setattr(art, key, payload[key])
    db.commit()
    db.refresh(art)
    return artifact_to_response(art, db)


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

# --- NEW PAYMENT FLOW SIMULATION ---

@app.post("/payments/create", response_model=schemas.OrderResponse)
def create_payment(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    # Calculate amount based on ticket type
    # Base price could be fetched from museum, but for simplicity:
    base_price = 30000
    if ticket.ticket_type == "Student":
        amount = int(base_price * 0.7)
    elif ticket.ticket_type == "Children":
        amount = int(base_price * 0.5)
    elif ticket.ticket_type == "Preview":
        amount = 5000
    else:
        amount = base_price

    today_date = str(date.today())

    # Create Order
    new_order = models.Order(
        user_id=ticket.user_id,
        museum_id=ticket.museum_id,
        ticket_type=ticket.ticket_type,
        amount=amount,
        status="PENDING",
        created_at=today_date
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Generate VietQR URL (Mock details for Demo)
    # format: https://img.vietqr.io/image/<BIN>-<RECEIVER_NUMBER>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<DESCRIPTION>&accountName=<ACCOUNT_NAME>
    bank_bin = "970436"  # Vietcombank BIN for demo
    account_no = "1122334455"
    description = f"PAY ORDER {new_order.id}"
    qr_url = f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png?amount={amount}&addInfo={description}&accountName=MUSEAMIGO"

    return {"order_id": new_order.id, "status": new_order.status, "qr_url": qr_url}

@app.get("/payments/{order_id}/status", response_model=schemas.PaymentStatusResponse)
def check_payment_status(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    response = {"status": order.status, "ticket": None}

    if order.status == "PAID":
        # Find the ticket created for this order.
        # For simplicity, we find the most recent ticket for this user and museum created today.
        ticket = db.query(models.Ticket).filter(
            models.Ticket.user_id == order.user_id,
            models.Ticket.museum_id == order.museum_id,
            models.Ticket.ticket_type == order.ticket_type
        ).order_by(models.Ticket.id.desc()).first()

        response["ticket"] = ticket

    return response

@app.post("/payments/{order_id}/webhook")
def simulate_payment_webhook(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "PAID":
        return {"message": "Order already paid"}

    # Mark as PAID
    order.status = "PAID"
    order.paid_at = str(date.today())

    # Generate the ticket
    random_string = uuid.uuid4().hex[:8].upper()
    unique_qr = f"MUSEUM-{order.museum_id}-USER-{order.user_id}-{random_string}"

    new_ticket = models.Ticket(
        ticket_type=order.ticket_type,
        purchase_date=order.created_at,
        qr_code=unique_qr,
        user_id=order.user_id,
        museum_id=order.museum_id
    )

    db.add(new_ticket)
    db.commit()

    return {"message": "Webhook processed, order paid, ticket generated"}

@app.get("/users/{user_id}/tickets")
def get_user_tickets(user_id: int, db: Session = Depends(get_db)):
    tickets = db.query(models.Ticket).filter(models.Ticket.user_id == user_id).all()
    result = []
    for t in tickets:
        museum = db.query(models.Museum).filter(models.Museum.id == t.museum_id).first()
        result.append({
            "id": t.id,
            "ticket_type": t.ticket_type,
            "purchase_date": t.purchase_date,
            "qr_code": t.qr_code,
            "is_used": t.is_used,
            "user_id": t.user_id,
            "museum_id": t.museum_id,
            "museum_name": museum.name if museum else "Unknown Museum",
        })
    return result


@app.post(
    "/users/{user_id}/tickets/mark-used",
    response_model=schemas.MarkTicketUsedResponse,
)
def mark_ticket_used(
    user_id: int,
    payload: schemas.MarkTicketUsedRequest,
    db: Session = Depends(get_db),
):
    """Mark a ticket as used when the visitor taps **I'm in** (entrance check-in)."""
    qr_code = payload.qr_code.strip()
    if not qr_code:
        raise HTTPException(status_code=400, detail="qr_code is required")

    ticket = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.qr_code == qr_code,
            models.Ticket.user_id == user_id,
        )
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found for this user")

    if ticket.is_used:
        return schemas.MarkTicketUsedResponse(
            message="Already marked as used",
            ticket_id=ticket.id,
            is_used=True,
        )

    ticket.is_used = True
    db.commit()
    db.refresh(ticket)
    return schemas.MarkTicketUsedResponse(
        message="Ticket marked as used",
        ticket_id=ticket.id,
        is_used=True,
    )


@app.post("/tickets/redeem", response_model=schemas.RedeemTicketResponse)
def redeem_ticket_for_user(
    payload: schemas.RedeemTicketRequest,
    db: Session = Depends(get_db),
):
    """
    Assign an unused ticket (same QR / code as printed on the friend's receipt)
    to the signed-in user so they can use it on another device/account.
    """
    code = payload.ticket_code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="ticket_code is required")

    ticket = (
        db.query(models.Ticket).filter(models.Ticket.qr_code == code).first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket code not found")

    if ticket.is_used:
        raise HTTPException(
            status_code=400,
            detail="This ticket has already been used",
        )

    ticket.user_id = payload.user_id
    db.commit()
    db.refresh(ticket)

    museum = (
        db.query(models.Museum).filter(models.Museum.id == ticket.museum_id).first()
    )
    return schemas.RedeemTicketResponse(
        id=ticket.id,
        ticket_type=ticket.ticket_type or "",
        purchase_date=ticket.purchase_date or "",
        qr_code=ticket.qr_code or "",
        is_used=ticket.is_used,
        user_id=ticket.user_id,
        museum_id=ticket.museum_id,
        museum_name=museum.name if museum else "Unknown Museum",
    )


# --- PHASE 3: Fetch Navigation Routes ---
@app.get("/museums/{museum_id}/routes", response_model=list[schemas.RouteResponse])
def get_routes(museum_id: int, db: Session = Depends(get_db)):
    routes = db.query(models.Route).filter(models.Route.museum_id == museum_id).all()
    out: list[schemas.RouteResponse] = []
    for r in routes:
        parsed: list[schemas.RouteStopPayload] = []
        raw = (r.stops_json or "").strip()
        if raw:
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, list):
                    for x in loaded:
                        if not isinstance(x, dict):
                            continue
                        label = str(x.get("label") or "").strip()
                        if not label:
                            continue
                        item_type = str(x.get("item_type") or "custom").strip().lower()
                        if item_type not in ("artifact", "exhibition", "map_place", "custom"):
                            item_type = "custom"
                        item_id = x.get("item_id")
                        parsed.append(
                            schemas.RouteStopPayload(
                                item_type=item_type,
                                item_id=int(item_id) if isinstance(item_id, int) else None,
                                label=label,
                            )
                        )
            except Exception:
                parsed = []
        out.append(
            schemas.RouteResponse(
                id=r.id,
                name=r.name or "",
                estimated_time=r.estimated_time or "",
                stops_count=len(parsed),
                stops_json=parsed,
                museum_id=r.museum_id,
            )
        )
    return out

# --- PHASE 3.5: Get Achievements for a Route ---
@app.get("/museums/{museum_id}/routes/{route_id}/achievements")
def get_route_achievements(museum_id: int, route_id: int, db: Session = Depends(get_db)):
    achievements = db.query(models.Achievement).filter(
        models.Achievement.museum_id == museum_id
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
def get_user_achievements(user_id: int, museum_id: int = Query(..., description="Museum ID to get achievements for"), db: Session = Depends(get_db)):

    # Get achievements for the specified museum only
    all_achievements = db.query(models.Achievement).filter(
        models.Achievement.museum_id == museum_id
    ).all()

    # Get user's completed achievements for this museum
    user_achievements = db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user_id,
        models.UserAchievement.museum_id == museum_id
    ).all()

    completed_achievements = {
        ua.achievement_id: ua for ua in user_achievements
    }

    # Calculate scan count for THIS museum only
    user_collections = db.query(models.Collection).filter(
        models.Collection.user_id == user_id
    ).all()

    artifact_ids = [c.artifact_id for c in user_collections]
    artifacts = db.query(models.Artifact).filter(
        models.Artifact.id.in_(artifact_ids),
        models.Artifact.museum_id == museum_id
    ).all()

    museum_scan_count = len(artifacts)

    # Calculate total points from completed achievements for this museum
    total_points = sum(
        ach.points
        for ach in db.query(models.Achievement)
        .join(models.UserAchievement, models.Achievement.id == models.UserAchievement.achievement_id)
        .filter(
            models.UserAchievement.user_id == user_id,
            models.UserAchievement.museum_id == museum_id,
            models.UserAchievement.is_completed == True
        )
        .all()
    )

    # Check and update achievement progress
    achievements_response = []
    for achievement in all_achievements:
        is_completed = False
        progress = 0

        if achievement.id in completed_achievements:
            is_completed = completed_achievements[achievement.id].is_completed
        else:
            if achievement.requirement_type == "museum_scan_count":
                progress = min(museum_scan_count, achievement.requirement_value)
                if museum_scan_count >= achievement.requirement_value:
                    is_completed = True

            # Auto-complete achievement if criteria met
            if is_completed:
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
        "museum_id": museum_id,
        "total_points": total_points,
        "unlocked_count": museum_scan_count,
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
    db_user.font_size = settings.font_size
    db_user.scheme = settings.scheme

    # 4. Save the changes to MySQL
    db.commit()
    db.refresh(db_user)

    return db_user

# --- PHASE 5: Ogima AI Chat Assistant ---
@app.post("/ai/chat", response_model=schemas.ChatResponse)
def chat_with_ogima(chat_request: schemas.ChatRequest):

    # Keep allowed actions explicit for safer client handling.
    allowed_actions = {"NAVIGATE", "SETTINGS_UPDATE"}

    def _normalize_action(value):
        if value is None:
            return None
        candidate = str(value).strip().upper()
        return candidate if candidate in allowed_actions else None

    user_input = {"messages": [
        ("system", ogima_system_message),
        ("user", chat_request.message)
    ]}

    try:
        # 2. Run the AI loop (Think -> Search DB -> Generate Answer)
        final_state = agent_executor.invoke(user_input)

        # 3. Extract the final text reply
        ai_reply = final_state["messages"][-1].content
        raw_content = ai_reply if isinstance(ai_reply, str) else json.dumps(ai_reply)

        # 4. Parse structured JSON output from the model.
        # Fallback to plain text reply if the model returns non-JSON content.
        try:
            parsed = json.loads(raw_content)
            reply_text = str(parsed.get("reply", "")).strip()
            action = _normalize_action(parsed.get("action"))

            if not reply_text:
                reply_text = raw_content

            return {"reply": reply_text, "action": action}
        except Exception:
            return {"reply": raw_content, "action": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/chat/audio")
async def chat_with_ogima_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # Tạo tên file duy nhất bằng UUID để tránh xung đột khi nhiều người dùng cùng lúc
    unique_id = str(uuid.uuid4())
    temp_input_path = TEMP_DIR / f"input_{unique_id}.wav"
    temp_output_path = TEMP_DIR / f"output_{unique_id}.wav"

    # Đăng ký xóa file sau khi phản hồi xong (dùng str() vì os.remove cần string path)
    background_tasks.add_task(os.remove, str(temp_input_path))
    background_tasks.add_task(os.remove, str(temp_output_path))

    try:
        # 1. Lưu audio vào folder ./temp/
        audio_bytes = await file.read()
        with open(temp_input_path, "wb") as f:
            f.write(audio_bytes)

        # 2. Audio -> Text (STT) - Truyền string path vào hàm
        user_message_text = await audio_to_text(str(temp_input_path))

        # 3. Logic AI
        ai_reply_text = get_ogima_response(user_message_text)

        # 4. Text -> Audio (TTS) - Lưu vào folder ./temp/
        await text_to_audio(
            text=ai_reply_text,
            output_file=str(temp_output_path),
            voice_name="Aoede"
        )

        # 5. Trả về file audio
        return FileResponse(
            path=str(temp_output_path),
            media_type="audio/wav",
            filename="response.wav"
        )

    except Exception as e:
        print(f"Lỗi API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)