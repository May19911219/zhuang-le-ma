import json

from sqlalchemy.orm import Session

from app.catalog import PRESETS
from app.models import Software


def seed_software(db: Session) -> None:
    """把预置软件写入数据库，已存在的 slug 会跳过。"""
    existing = {row.slug for row in db.query(Software.slug).all()}
    for item in PRESETS:
        if item["slug"] in existing:
            continue
        db.add(
            Software(
                name=item["name"],
                slug=item["slug"],
                source_type=item["source_type"],
                source_ref=item["source_ref"],
                install_type=item["install_type"],
                official_url=item["official_url"],
                aliases=json.dumps(item["aliases"], ensure_ascii=False),
                fallback_versions=json.dumps(item["fallback_versions"], ensure_ascii=False),
            )
        )
    db.commit()
