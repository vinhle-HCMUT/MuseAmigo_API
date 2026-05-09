from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Optional

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
    font_size: str
    scheme: str
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
    artifacts: Optional[List[str]] = None

    @field_validator("artifacts", mode="before")
    @classmethod
    def normalize_artifacts(cls, v):
        if v is None:
            return []
        return v

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

class OrderResponse(BaseModel):
    order_id: int
    status: str
    qr_url: str

class PaymentStatusResponse(BaseModel):
    status: str
    ticket: TicketResponse | None = None

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

class UserUpdate(BaseModel):
    full_name: str | None = None

# Schema for admin to update any user fields
class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    theme: str | None = None
    language: str | None = None
    font_size: str | None = None
    scheme: str | None = None

class UserSettingsUpdate(BaseModel):
    theme: str
    language: str
    font_size: str
    scheme: str

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
    action: Literal["NAVIGATE", "SETTINGS_UPDATE"] | None = None


# --- Staff dashboard ---
class StaffLoginRequest(BaseModel):
    email: str
    password: str


class StaffMeResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    managed_museum_id: int | None


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: StaffMeResponse


class MuseumUpdate(BaseModel):
    name: str | None = None
    operating_hours: str | None = None
    base_ticket_price: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class ArtifactCreate(BaseModel):
    artifact_code: str
    title: str
    year: str
    description: str
    is_3d_available: bool = False
    unity_prefab_name: str = ""
    audio_asset: str = ""


class ArtifactUpdate(BaseModel):
    artifact_code: str | None = None
    title: str | None = None
    year: str | None = None
    description: str | None = None
    is_3d_available: bool | None = None
    unity_prefab_name: str | None = None
    audio_asset: str | None = None
    museum_id: int | None = None


class ExhibitionCreate(BaseModel):
    name: str
    location: str
    artifacts: list[str] | None = None


class ExhibitionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    artifacts: list[str] | None = None


class RouteCreate(BaseModel):
    name: str
    estimated_time: str
    stops_count: int


class RouteUpdate(BaseModel):
    name: str | None = None
    estimated_time: str | None = None
    stops_count: int | None = None


class AchievementCreate(BaseModel):
    name: str
    description: str
    requirement_type: str = "museum_scan_count"
    requirement_value: int
    points: int = 50


class AchievementUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    requirement_type: str | None = None
    requirement_value: int | None = None
    points: int | None = None


UserRole = Literal["superadmin", "manager", "visitor"]


class UserAdminDetailResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    managed_museum_id: int | None
    is_active: bool
    theme: str
    language: str
    font_size: str
    scheme: str
    reset_token: str | None = None
    reset_token_expires: str | None = None

    class Config:
        from_attributes = True


class SuperadminUserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: UserRole = "visitor"
    managed_museum_id: int | None = None
    is_active: bool = True
    theme: str = "light"
    language: str = "English"
    font_size: str = "Medium"
    scheme: str = "0xFFCC353A"


class SuperadminUserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    password: str | None = None
    role: UserRole | None = None
    managed_museum_id: int | None = None
    is_active: bool | None = None
    theme: str | None = None
    language: str | None = None
    font_size: str | None = None
    scheme: str | None = None
    reset_token: str | None = None
    reset_token_expires: str | None = None


class MuseumVisitorStats(BaseModel):
    museum_id: int
    museum_name: str
    tickets_total: int
    tickets_used: int
    unique_visitors_with_ticket: int
    orders_total: int
    orders_paid: int
    revenue_paid_vnd: int
    artifact_scans_total: int
    unique_visitors_with_scan: int
    unique_visitors_engaged: int
    achievements_completed: int


class VisitorStatsSummary(BaseModel):
    museum_rows: int
    registered_visitor_accounts: int
    tickets_total: int
    tickets_used: int
    unique_visitors_with_ticket: int
    orders_total: int
    orders_paid: int
    revenue_paid_vnd: int
    artifact_scans_total: int
    unique_visitors_with_scan: int
    unique_visitors_engaged: int
    achievements_completed: int


class VisitorStatsOrderPeriod(BaseModel):
    """When set, order/revenue figures below use this window (inclusive YYYY-MM-DD)."""

    date_from: str | None = None
    date_to: str | None = None
    orders_total_basis: Literal["created_at"] = "created_at"
    revenue_basis: Literal["paid_at_fallback_created_at"] = "paid_at_fallback_created_at"


class VisitorTicketBuyerRow(BaseModel):
    """Visitor (app user) and how many tickets they hold in scope (per museum filter)."""

    user_id: int
    full_name: str
    email: str
    tickets_count: int


class DailyFinancialRow(BaseModel):
    """One calendar day in the financial chart (scoped museums)."""

    date: str
    orders_total: int
    revenue_paid_vnd: int
    ai_cost_vnd: int
    museum_payout_vnd: int
    total_income_vnd: int


class VisitorStatsResponse(BaseModel):
    """order_revenue_period: when set, orders/revenue and ticket_buyers use that inclusive date window; scans stay all-time unless noted."""

    scope: Literal["all_museums", "single_museum"]
    registered_visitor_accounts: int
    museums: list[MuseumVisitorStats]
    summary: VisitorStatsSummary | None = None
    order_revenue_period: VisitorStatsOrderPeriod | None = None
    ticket_buyers: list[VisitorTicketBuyerRow] = Field(default_factory=list)
    daily_chart_period: VisitorStatsOrderPeriod | None = None
    daily_financials: list[DailyFinancialRow] = Field(default_factory=list)

