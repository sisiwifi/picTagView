from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.models.tag import Tag

# Initial scheme: assign by tag id order, cycle every 7 tags.
TAG_COLOR_SCHEME: list[dict[str, str]] = [
    {
        "color": "#FF0000",
        "border_color": "#FF0000",
        "background_color": "rgba(255, 0, 0, 0.40)",
    },
    {
        "color": "#FF6600",
        "border_color": "#FF6600",
        "background_color": "rgba(255, 102, 0, 0.40)",
    },
    {
        "color": "#C9A600",
        "border_color": "#C9A600",
        "background_color": "rgba(255, 255, 0, 0.14)",
    },
    {
        "color": "#00B84A",
        "border_color": "#00B84A",
        "background_color": "rgba(0, 255, 0, 0.16)",
    },
    {
        "color": "#1E90FF",
        "border_color": "#1E90FF",
        "background_color": "rgba(30, 144, 255, 0.40)",
    },
    {
        "color": "#8A2BE2",
        "border_color": "#8A2BE2",
        "background_color": "rgba(138, 43, 226, 0.40)",
    },
    {
        "color": "#FF1493",
        "border_color": "#FF1493",
        "background_color": "rgba(255, 20, 147, 0.40)",
    },
]


def _safe_dict(raw: object) -> dict:
    return dict(raw) if isinstance(raw, dict) else {}


def _style_for_index(index: int) -> dict[str, str]:
    return TAG_COLOR_SCHEME[index % len(TAG_COLOR_SCHEME)]


def _build_next_metadata(raw_metadata: object, style: dict[str, str]) -> dict:
    metadata = _safe_dict(raw_metadata)
    next_metadata = dict(metadata)
    next_metadata["color"] = style["color"]
    next_metadata["border_color"] = style["border_color"]
    next_metadata["background_color"] = style["background_color"]

    ui_hint = _safe_dict(next_metadata.get("ui_hint"))
    ui_hint["tag_chip"] = {
        "color": style["color"],
        "border_color": style["border_color"],
        "background_color": style["background_color"],
        "scheme": "id_order_cycle_v1",
    }
    next_metadata["ui_hint"] = ui_hint
    return next_metadata


def ensure_tag_style_scheme(session: Session) -> None:
    tags = session.exec(select(Tag).order_by(Tag.id)).all()
    changed = False
    for index, tag in enumerate(tags):
        style = _style_for_index(index)
        next_metadata = _build_next_metadata(tag.metadata_, style)
        if next_metadata == _safe_dict(tag.metadata_):
            continue
        tag.metadata_ = next_metadata
        tag.updated_at = datetime.utcnow()
        session.add(tag)
        changed = True

    if changed:
        session.commit()
