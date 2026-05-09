from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
from database import get_db
from staff_auth import (
    effective_role,
    ensure_museum_scope,
    get_current_staff,
    get_current_superadmin,
)

router = APIRouter()


def _parse_opt_date_param(value: str | None) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date; use YYYY-MM-DD (ISO).",
        ) from None


def _order_payment_date_expr():
    """Date string YYYY-MM-DD for when payment completed (paid_at, else legacy created_at)."""
    return func.coalesce(
        func.nullif(models.Order.paid_at, ""),
        func.nullif(models.Order.created_at, ""),
    )


def _staff_me(user: models.User) -> schemas.StaffMeResponse:
    return schemas.StaffMeResponse(
        id=user.id,
        full_name=user.full_name or "",
        email=user.email or "",
        role=effective_role(user),
        managed_museum_id=user.managed_museum_id,
    )


@router.get("/me", response_model=schemas.StaffMeResponse)
def dashboard_me(user: models.User = Depends(get_current_staff)):
    return _staff_me(user)


@router.get("/museums", response_model=list[schemas.MuseumResponse])
def list_museums_dashboard(
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    if effective_role(user) == "superadmin":
        return db.query(models.Museum).order_by(models.Museum.id).all()
    if effective_role(user) == "manager":
        if not user.managed_museum_id:
            return []
        m = (
            db.query(models.Museum)
            .filter(models.Museum.id == user.managed_museum_id)
            .first()
        )
        return [m] if m else []
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.patch("/museums/{museum_id}", response_model=schemas.MuseumResponse)
def update_museum_dashboard(
    museum_id: int,
    data: schemas.MuseumUpdate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    m = db.query(models.Museum).filter(models.Museum.id == museum_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Museum not found")
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.get(
    "/museums/{museum_id}/artifacts",
    response_model=list[schemas.ArtifactResponse],
)
def list_artifacts_dashboard(
    museum_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    return (
        db.query(models.Artifact)
        .filter(models.Artifact.museum_id == museum_id)
        .order_by(models.Artifact.id)
        .all()
    )


@router.post(
    "/museums/{museum_id}/artifacts",
    response_model=schemas.ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_artifact_dashboard(
    museum_id: int,
    data: schemas.ArtifactCreate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    code = data.artifact_code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="artifact_code is required")
    art = models.Artifact(
        artifact_code=code,
        title=data.title.strip(),
        year=data.year.strip(),
        description=data.description.strip(),
        is_3d_available=data.is_3d_available,
        unity_prefab_name=data.unity_prefab_name.strip(),
        audio_asset=(data.audio_asset or "").strip(),
        museum_id=museum_id,
    )
    db.add(art)
    try:
        db.commit()
        db.refresh(art)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Artifact code must be unique")
    return art


@router.put("/artifacts/{artifact_id}", response_model=schemas.ArtifactResponse)
def update_artifact_dashboard(
    artifact_id: int,
    data: schemas.ArtifactUpdate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    art = db.query(models.Artifact).filter(models.Artifact.id == artifact_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    ensure_museum_scope(user, art.museum_id)
    payload = data.model_dump(exclude_unset=True)
    if "museum_id" in payload and payload["museum_id"] is not None:
        new_mid = payload["museum_id"]
        if effective_role(user) != "superadmin":
            raise HTTPException(
                status_code=403, detail="Only superadmin can move artifacts between museums"
            )
        ensure_museum_scope(user, new_mid)
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
        setattr(art, k, v)
    try:
        db.commit()
        db.refresh(art)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Artifact code must be unique")
    return art


@router.delete("/artifacts/{artifact_id}")
def delete_artifact_dashboard(
    artifact_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    art = db.query(models.Artifact).filter(models.Artifact.id == artifact_id).first()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    ensure_museum_scope(user, art.museum_id)
    db.query(models.Collection).filter(
        models.Collection.artifact_id == artifact_id
    ).delete(synchronize_session=False)
    db.delete(art)
    db.commit()
    return {"message": "Artifact deleted"}


@router.get(
    "/museums/{museum_id}/exhibitions",
    response_model=list[schemas.ExhibitionResponse],
)
def list_exhibitions_dashboard(
    museum_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    rows = (
        db.query(models.Exhibition)
        .filter(models.Exhibition.museum_id == museum_id)
        .order_by(models.Exhibition.id)
        .all()
    )
    return rows


@router.post(
    "/museums/{museum_id}/exhibitions",
    response_model=schemas.ExhibitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exhibition_dashboard(
    museum_id: int,
    data: schemas.ExhibitionCreate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    ex = models.Exhibition(
        name=data.name.strip(),
        location=data.location.strip(),
        museum_id=museum_id,
        artifacts=data.artifacts if data.artifacts is not None else [],
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


@router.put("/exhibitions/{exhibition_id}", response_model=schemas.ExhibitionResponse)
def update_exhibition_dashboard(
    exhibition_id: int,
    data: schemas.ExhibitionUpdate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ex = (
        db.query(models.Exhibition)
        .filter(models.Exhibition.id == exhibition_id)
        .first()
    )
    if not ex:
        raise HTTPException(status_code=404, detail="Exhibition not found")
    ensure_museum_scope(user, ex.museum_id)
    if data.name is not None:
        ex.name = data.name.strip()
    if data.location is not None:
        ex.location = data.location.strip()
    if data.artifacts is not None:
        ex.artifacts = data.artifacts
    db.commit()
    db.refresh(ex)
    return ex


@router.delete("/exhibitions/{exhibition_id}")
def delete_exhibition_dashboard(
    exhibition_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ex = (
        db.query(models.Exhibition)
        .filter(models.Exhibition.id == exhibition_id)
        .first()
    )
    if not ex:
        raise HTTPException(status_code=404, detail="Exhibition not found")
    ensure_museum_scope(user, ex.museum_id)
    db.delete(ex)
    db.commit()
    return {"message": "Exhibition deleted"}


@router.get("/museums/{museum_id}/routes", response_model=list[schemas.RouteResponse])
def list_routes_dashboard(
    museum_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    return (
        db.query(models.Route)
        .filter(models.Route.museum_id == museum_id)
        .order_by(models.Route.id)
        .all()
    )


@router.post(
    "/museums/{museum_id}/routes",
    response_model=schemas.RouteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_route_dashboard(
    museum_id: int,
    data: schemas.RouteCreate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    r = models.Route(
        name=data.name.strip(),
        estimated_time=data.estimated_time.strip(),
        stops_count=data.stops_count,
        museum_id=museum_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/routes/{route_id}", response_model=schemas.RouteResponse)
def update_route_dashboard(
    route_id: int,
    data: schemas.RouteUpdate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    r = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Route not found")
    ensure_museum_scope(user, r.museum_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/routes/{route_id}")
def delete_route_dashboard(
    route_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    r = db.query(models.Route).filter(models.Route.id == route_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Route not found")
    ensure_museum_scope(user, r.museum_id)
    db.delete(r)
    db.commit()
    return {"message": "Route deleted"}


@router.get(
    "/museums/{museum_id}/achievements",
    response_model=list[schemas.AchievementResponse],
)
def list_achievements_dashboard(
    museum_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    return (
        db.query(models.Achievement)
        .filter(models.Achievement.museum_id == museum_id)
        .order_by(models.Achievement.id)
        .all()
    )


@router.post(
    "/museums/{museum_id}/achievements",
    response_model=schemas.AchievementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_achievement_dashboard(
    museum_id: int,
    data: schemas.AchievementCreate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    ensure_museum_scope(user, museum_id)
    a = models.Achievement(
        name=data.name.strip(),
        description=data.description.strip(),
        requirement_type=data.requirement_type.strip(),
        requirement_value=data.requirement_value,
        points=data.points,
        museum_id=museum_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.put(
    "/achievements/{achievement_id}",
    response_model=schemas.AchievementResponse,
)
def update_achievement_dashboard(
    achievement_id: int,
    data: schemas.AchievementUpdate,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    a = (
        db.query(models.Achievement)
        .filter(models.Achievement.id == achievement_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Achievement not found")
    if a.museum_id is None:
        raise HTTPException(status_code=403, detail="Cannot edit global achievement here")
    ensure_museum_scope(user, a.museum_id)
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/achievements/{achievement_id}")
def delete_achievement_dashboard(
    achievement_id: int,
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    a = (
        db.query(models.Achievement)
        .filter(models.Achievement.id == achievement_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Achievement not found")
    if a.museum_id is None:
        raise HTTPException(status_code=403, detail="Cannot delete global achievement here")
    ensure_museum_scope(user, a.museum_id)
    db.query(models.UserAchievement).filter(
        models.UserAchievement.achievement_id == achievement_id
    ).delete(synchronize_session=False)
    db.delete(a)
    db.commit()
    return {"message": "Achievement deleted"}


def _apply_user_role_rules(u: models.User) -> None:
    r = (u.role or "").strip()
    if r in ("", "user"):
        u.role = "visitor"
        r = "visitor"
    if r == "museum_manager":
        u.role = "manager"
        r = "manager"
    if r in ("superadmin", "visitor"):
        u.managed_museum_id = None
    elif r == "manager" and u.managed_museum_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manager role requires managed_museum_id",
        )


@router.get(
    "/users",
    response_model=list[schemas.UserAdminDetailResponse],
)
def superadmin_list_users(
    _: models.User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.id).all()


@router.get(
    "/users/{user_id}",
    response_model=schemas.UserAdminDetailResponse,
)
def superadmin_get_user(
    user_id: int,
    _: models.User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.post(
    "/users",
    response_model=schemas.UserAdminDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def superadmin_create_user(
    data: schemas.SuperadminUserCreate,
    _: models.User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    if not data.password or len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    mid = data.managed_museum_id
    if data.role == "manager":
        if mid is None:
            raise HTTPException(
                status_code=400,
                detail="Manager role requires managed_museum_id",
            )
    else:
        mid = None
    u = models.User(
        full_name=data.full_name.strip(),
        email=data.email.strip(),
        hashed_password=data.password,
        role=data.role,
        managed_museum_id=mid,
        is_active=data.is_active,
        theme=data.theme,
        language=data.language,
        font_size=data.font_size,
        scheme=data.scheme,
    )
    db.add(u)
    try:
        db.commit()
        db.refresh(u)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    return u


@router.put(
    "/users/{user_id}",
    response_model=schemas.UserAdminDetailResponse,
)
def superadmin_update_user(
    user_id: int,
    data: schemas.SuperadminUserUpdate,
    admin: models.User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    _unset = object()
    provided = data.model_dump(exclude_unset=True)
    payload = dict(provided)

    if "password" in payload:
        pw = payload.pop("password")
        if pw is not None and str(pw).strip() != "":
            if len(pw) < 6:
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 6 characters",
                )
            u.hashed_password = pw

    role_new = payload.pop("role") if "role" in provided else _unset
    museum_new = (
        payload.pop("managed_museum_id")
        if "managed_museum_id" in provided
        else _unset
    )

    for k, v in list(payload.items()):
        if k == "password":
            continue
        if k == "email" and v is not None:
            v = str(v).strip()
        if k == "full_name" and v is not None:
            v = str(v).strip()
        setattr(u, k, v)

    if role_new is not _unset:
        u.role = role_new
    if museum_new is not _unset:
        mid = museum_new
        if mid is not None:
            m = db.query(models.Museum).filter(models.Museum.id == mid).first()
            if not m:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="managed_museum_id does not match any museum",
                )
        u.managed_museum_id = mid

    _apply_user_role_rules(u)
    try:
        db.commit()
        db.refresh(u)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already in use")
    return u


@router.delete("/users/{user_id}")
def superadmin_delete_user(
    user_id: int,
    admin: models.User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(models.Collection).filter(
        models.Collection.user_id == user_id
    ).delete(synchronize_session=False)
    db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user_id
    ).delete(synchronize_session=False)
    db.query(models.Ticket).filter(models.Ticket.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.Order).filter(models.Order.user_id == user_id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
    return {"message": f"User {user_id} deleted"}


def _registered_visitor_account_count(db: Session) -> int:
    """Users who are not staff (visitor / app accounts)."""
    return (
        db.query(func.count(models.User.id))
        .filter(
            or_(
                models.User.role.is_(None),
                models.User.role == "",
                ~models.User.role.in_(
                    ["superadmin", "manager", "museum_manager"]
                ),
            )
        )
        .scalar()
        or 0
    )


def _ticket_buyer_rows(
    db: Session,
    museum_ids: list[int],
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
) -> list[schemas.VisitorTicketBuyerRow]:
    """Count tickets per visitor user in museum scope; optional YYYY-MM-DD window on purchase_date."""
    if not museum_ids:
        return []
    tc = func.count(models.Ticket.id)
    q = (
        db.query(models.Ticket.user_id, tc)
        .filter(
            models.Ticket.museum_id.in_(museum_ids),
            models.Ticket.user_id.isnot(None),
        )
    )
    if date_from is not None:
        q = q.filter(
            models.Ticket.purchase_date.isnot(None),
            models.Ticket.purchase_date >= date_from.isoformat(),
        )
    if date_to is not None:
        q = q.filter(models.Ticket.purchase_date <= date_to.isoformat())
    agg = (
        q.group_by(models.Ticket.user_id)
        .order_by(desc(tc))
        .limit(limit)
        .all()
    )
    if not agg:
        return []
    uids = [row[0] for row in agg if row[0] is not None]
    users = {
        u.id: u
        for u in db.query(models.User).filter(models.User.id.in_(uids)).all()
    }
    out: list[schemas.VisitorTicketBuyerRow] = []
    for uid, count in agg:
        if uid is None:
            continue
        u = users.get(uid)
        out.append(
            schemas.VisitorTicketBuyerRow(
                user_id=int(uid),
                full_name=(u.full_name or "—") if u else "—",
                email=(u.email or "—") if u else "—",
                tickets_count=int(count or 0),
            )
        )
    return out


# Match dashboard stats demo constants (AI cost split across chart days).
_DEMO_AI_REQUESTS = 1847
_DEMO_AI_USD_PER_1K = 10
_DEMO_VND_PER_USD = 25500
_PLATFORM_FEE_RATE_DAILY = 0.25


def _total_demo_ai_vnd() -> int:
    return round(
        (_DEMO_AI_REQUESTS / 1000.0) * _DEMO_AI_USD_PER_1K * _DEMO_VND_PER_USD
    )


def _chart_date_bounds(
    d_from: date | None, d_to: date | None
) -> tuple[date, date]:
    """When both params None, use last 30 calendar days ending today (inclusive)."""
    today = date.today()
    if d_from is not None and d_to is not None:
        return d_from, d_to
    if d_from is not None and d_to is None:
        return d_from, today
    if d_from is None and d_to is not None:
        return d_to - timedelta(days=29), d_to
    return today - timedelta(days=29), today


def _daily_financial_rows(
    db: Session,
    museum_ids: list[int],
    chart_from: date,
    chart_to: date,
) -> list[schemas.DailyFinancialRow]:
    """Per-day orders (created date) and paid revenue (payment date); AI split evenly across days."""
    if not museum_ids:
        return []

    cday = func.substr(models.Order.created_at, 1, 10)
    q_ot = (
        db.query(cday, func.count(models.Order.id))
        .filter(models.Order.museum_id.in_(museum_ids))
        .filter(models.Order.created_at.isnot(None))
        .filter(cday >= chart_from.isoformat())
        .filter(cday <= chart_to.isoformat())
    )
    orders_by_day: dict[str, int] = {}
    for ds, cnt in q_ot.group_by(cday).all():
        if ds:
            orders_by_day[str(ds)] = int(cnt or 0)

    pay_expr = _order_payment_date_expr()
    pday = func.substr(pay_expr, 1, 10)
    q_rev = (
        db.query(pday, func.coalesce(func.sum(models.Order.amount), 0))
        .filter(
            models.Order.museum_id.in_(museum_ids),
            models.Order.status == "PAID",
        )
        .filter(pday >= chart_from.isoformat())
        .filter(pday <= chart_to.isoformat())
    )
    rev_by_day: dict[str, int] = {}
    for ds, amt in q_rev.group_by(pday).all():
        if ds:
            rev_by_day[str(ds)] = int(amt or 0)

    total_ai = _total_demo_ai_vnd()
    days: list[date] = []
    cur = chart_from
    while cur <= chart_to:
        days.append(cur)
        cur += timedelta(days=1)
    n = len(days)
    if n == 0:
        return []
    base_ai = total_ai // n
    rem_ai = total_ai % n

    out: list[schemas.DailyFinancialRow] = []
    for i, day in enumerate(days):
        ds = day.isoformat()
        rev = rev_by_day.get(ds, 0)
        ai_d = base_ai + (1 if i < rem_ai else 0)
        payout = int(round(rev * (1 - _PLATFORM_FEE_RATE_DAILY)))
        out.append(
            schemas.DailyFinancialRow(
                date=ds,
                orders_total=orders_by_day.get(ds, 0),
                revenue_paid_vnd=rev,
                ai_cost_vnd=ai_d,
                museum_payout_vnd=payout,
                total_income_vnd=rev + ai_d,
            )
        )
    return out


def _engaged_visitors_count(db: Session, museum_ids: list[int]) -> int:
    """Distinct users with at least one ticket or artifact scan in the given museums."""
    if not museum_ids:
        return 0
    q1 = db.query(models.Ticket.user_id).filter(
        models.Ticket.museum_id.in_(museum_ids)
    ).distinct()
    q2 = (
        db.query(models.Collection.user_id)
        .join(
            models.Artifact,
            models.Collection.artifact_id == models.Artifact.id,
        )
        .filter(models.Artifact.museum_id.in_(museum_ids))
        .distinct()
    )
    return q1.union(q2).count()


def _museum_visitor_stats_row(
    db: Session,
    museum: models.Museum,
    *,
    order_date_from: date | None = None,
    order_date_to: date | None = None,
) -> schemas.MuseumVisitorStats:
    mid = museum.id
    tickets_total = (
        db.query(func.count(models.Ticket.id))
        .filter(models.Ticket.museum_id == mid)
        .scalar()
        or 0
    )
    tickets_used = (
        db.query(func.count(models.Ticket.id))
        .filter(
            models.Ticket.museum_id == mid,
            models.Ticket.is_used.is_(True),
        )
        .scalar()
        or 0
    )
    unique_visitors_tickets = (
        db.query(func.count(func.distinct(models.Ticket.user_id)))
        .filter(models.Ticket.museum_id == mid)
        .scalar()
        or 0
    )

    use_order_window = order_date_from is not None or order_date_to is not None
    if not use_order_window:
        orders_total = (
            db.query(func.count(models.Order.id))
            .filter(models.Order.museum_id == mid)
            .scalar()
            or 0
        )
        orders_paid = (
            db.query(func.count(models.Order.id))
            .filter(
                models.Order.museum_id == mid,
                models.Order.status == "PAID",
            )
            .scalar()
            or 0
        )
        revenue_paid = (
            db.query(func.coalesce(func.sum(models.Order.amount), 0))
            .filter(
                models.Order.museum_id == mid,
                models.Order.status == "PAID",
            )
            .scalar()
            or 0
        )
    else:
        q_created = db.query(func.count(models.Order.id)).filter(
            models.Order.museum_id == mid
        )
        if order_date_from is not None:
            q_created = q_created.filter(
                models.Order.created_at >= order_date_from.isoformat()
            )
        if order_date_to is not None:
            q_created = q_created.filter(
                models.Order.created_at <= order_date_to.isoformat()
            )
        orders_total = int(q_created.scalar() or 0)

        pay_d = _order_payment_date_expr()
        paid_conds = [
            models.Order.museum_id == mid,
            models.Order.status == "PAID",
        ]
        if order_date_from is not None:
            paid_conds.append(pay_d >= order_date_from.isoformat())
        if order_date_to is not None:
            paid_conds.append(pay_d <= order_date_to.isoformat())
        orders_paid = (
            db.query(func.count(models.Order.id))
            .filter(and_(*paid_conds))
            .scalar()
            or 0
        )
        revenue_paid = (
            db.query(func.coalesce(func.sum(models.Order.amount), 0))
            .filter(and_(*paid_conds))
            .scalar()
            or 0
        )
    revenue_paid = int(revenue_paid)

    artifact_subq = db.query(models.Artifact.id).filter(
        models.Artifact.museum_id == mid
    )
    scans_total = (
        db.query(func.count(models.Collection.id))
        .filter(models.Collection.artifact_id.in_(artifact_subq))
        .scalar()
        or 0
    )
    unique_scanners = (
        db.query(func.count(func.distinct(models.Collection.user_id)))
        .filter(models.Collection.artifact_id.in_(artifact_subq))
        .scalar()
        or 0
    )
    achievements_completed = (
        db.query(func.count(models.UserAchievement.id))
        .filter(
            models.UserAchievement.museum_id == mid,
            models.UserAchievement.is_completed.is_(True),
        )
        .scalar()
        or 0
    )
    engaged = _engaged_visitors_count(db, [mid])
    return schemas.MuseumVisitorStats(
        museum_id=mid,
        museum_name=museum.name or "",
        tickets_total=int(tickets_total),
        tickets_used=int(tickets_used),
        unique_visitors_with_ticket=int(unique_visitors_tickets),
        orders_total=int(orders_total),
        orders_paid=int(orders_paid),
        revenue_paid_vnd=int(revenue_paid),
        artifact_scans_total=int(scans_total),
        unique_visitors_with_scan=int(unique_scanners),
        unique_visitors_engaged=int(engaged),
        achievements_completed=int(achievements_completed),
    )


@router.get("/stats/visitors", response_model=schemas.VisitorStatsResponse)
def visitor_statistics(
    user: models.User = Depends(get_current_staff),
    db: Session = Depends(get_db),
    date_from: str | None = Query(
        None,
        description="Inclusive YYYY-MM-DD. With date_to, limits orders (created_at) and paid revenue (paid_at, else created_at).",
    ),
    date_to: str | None = Query(
        None,
        description="Inclusive YYYY-MM-DD end of window.",
    ),
):
    d_from = _parse_opt_date_param(date_from)
    d_to = _parse_opt_date_param(date_to)
    if d_from and d_to and d_from > d_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to",
        )

    order_period = None
    if d_from is not None or d_to is not None:
        order_period = schemas.VisitorStatsOrderPeriod(
            date_from=d_from.isoformat() if d_from else None,
            date_to=d_to.isoformat() if d_to else None,
        )

    er = effective_role(user)
    if er == "superadmin":
        museums = db.query(models.Museum).order_by(models.Museum.id).all()
        scope = "all_museums"
    elif er == "manager":
        if not user.managed_museum_id:
            return schemas.VisitorStatsResponse(
                scope="single_museum",
                registered_visitor_accounts=_registered_visitor_account_count(db),
                museums=[],
                summary=None,
                order_revenue_period=order_period,
                ticket_buyers=[],
                daily_chart_period=None,
                daily_financials=[],
            )
        museums = (
            db.query(models.Museum)
            .filter(models.Museum.id == user.managed_museum_id)
            .all()
        )
        scope = "single_museum"
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    registered = _registered_visitor_account_count(db)
    rows = [
        _museum_visitor_stats_row(
            db,
            m,
            order_date_from=d_from,
            order_date_to=d_to,
        )
        for m in museums
    ]
    museum_ids = [m.id for m in museums]

    ticket_buyers = _ticket_buyer_rows(
        db,
        museum_ids,
        date_from=d_from,
        date_to=d_to,
    )

    chart_from, chart_to = _chart_date_bounds(d_from, d_to)
    daily_financials = _daily_financial_rows(db, museum_ids, chart_from, chart_to)
    daily_chart_period = schemas.VisitorStatsOrderPeriod(
        date_from=chart_from.isoformat(),
        date_to=chart_to.isoformat(),
    )

    summary = None
    if er == "superadmin":
        if museum_ids:
            ut = (
                db.query(func.count(func.distinct(models.Ticket.user_id)))
                .filter(models.Ticket.museum_id.in_(museum_ids))
                .scalar()
                or 0
            )
            us = (
                db.query(func.count(func.distinct(models.Collection.user_id)))
                .join(
                    models.Artifact,
                    models.Collection.artifact_id == models.Artifact.id,
                )
                .filter(models.Artifact.museum_id.in_(museum_ids))
                .scalar()
                or 0
            )
            summary = schemas.VisitorStatsSummary(
                museum_rows=len(rows),
                registered_visitor_accounts=registered,
                tickets_total=sum(r.tickets_total for r in rows),
                tickets_used=sum(r.tickets_used for r in rows),
                unique_visitors_with_ticket=int(ut),
                orders_total=sum(r.orders_total for r in rows),
                orders_paid=sum(r.orders_paid for r in rows),
                revenue_paid_vnd=sum(r.revenue_paid_vnd for r in rows),
                artifact_scans_total=sum(r.artifact_scans_total for r in rows),
                unique_visitors_with_scan=int(us),
                unique_visitors_engaged=_engaged_visitors_count(db, museum_ids),
                achievements_completed=sum(
                    r.achievements_completed for r in rows
                ),
            )
        else:
            summary = schemas.VisitorStatsSummary(
                museum_rows=0,
                registered_visitor_accounts=registered,
                tickets_total=0,
                tickets_used=0,
                unique_visitors_with_ticket=0,
                orders_total=0,
                orders_paid=0,
                revenue_paid_vnd=0,
                artifact_scans_total=0,
                unique_visitors_with_scan=0,
                unique_visitors_engaged=0,
                achievements_completed=0,
            )

    return schemas.VisitorStatsResponse(
        scope=scope,
        registered_visitor_accounts=registered,
        museums=rows,
        summary=summary,
        order_revenue_period=order_period,
        ticket_buyers=ticket_buyers,
        daily_chart_period=daily_chart_period,
        daily_financials=daily_financials,
    )
