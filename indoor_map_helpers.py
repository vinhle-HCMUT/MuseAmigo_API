"""Helpers for indoor map floor FKs (artifacts, exhibitions) and API responses."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas


def resolve_floor_id_for_museum(
    db: Session, museum_id: int, label: str | None
) -> int | None:
    if label is None:
        return None
    t = str(label).strip()
    if not t:
        return None
    fl = (
        db.query(models.MuseumFloor)
        .filter(
            models.MuseumFloor.museum_id == museum_id,
            models.MuseumFloor.label == t,
        )
        .first()
    )
    return fl.id if fl else None


def ensure_floor_belongs_to_museum(
    db: Session, museum_id: int, floor_id: int | None
) -> None:
    if floor_id is None:
        return
    fl = (
        db.query(models.MuseumFloor)
        .filter(
            models.MuseumFloor.id == floor_id,
            models.MuseumFloor.museum_id == museum_id,
        )
        .first()
    )
    if not fl:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="floor_id must belong to this museum",
        )


def floor_label_for_floor_id(db: Session, floor_id: int | None) -> str | None:
    if floor_id is None:
        return None
    fl = (
        db.query(models.MuseumFloor)
        .filter(models.MuseumFloor.id == floor_id)
        .first()
    )
    return fl.label if fl else None


def artifact_to_response(
    art: models.Artifact, db: Session
) -> schemas.ArtifactResponse:
    return schemas.ArtifactResponse(
        id=art.id,
        artifact_code=art.artifact_code,
        title=art.title,
        year=art.year,
        description=art.description,
        is_3d_available=art.is_3d_available,
        museum_id=art.museum_id,
        unity_prefab_name=art.unity_prefab_name,
        audio_asset=art.audio_asset or "",
        map_x=art.map_x,
        map_y=art.map_y,
        floor_id=art.floor_id,
        floor_label=floor_label_for_floor_id(db, art.floor_id),
    )


def exhibition_to_response(
    ex: models.Exhibition, db: Session
) -> schemas.ExhibitionResponse:
    return schemas.ExhibitionResponse(
        id=ex.id,
        name=ex.name,
        location=ex.location,
        museum_id=ex.museum_id,
        artifacts=ex.artifacts or [],
        map_x=ex.map_x,
        map_y=ex.map_y,
        floor_id=ex.floor_id,
        floor_label=floor_label_for_floor_id(db, ex.floor_id),
    )
