from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Feedback, Software
from app.schemas import FeedbackRequest, ParseRequest, PlanRequest
from app.services.plans import add_feedback, get_or_create_plan, list_versions, parse_query, plan_payload, software_payload

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    """供桌面端和管理后台确认服务已启动。"""
    return {"ok": True}


@router.get("/software")
def list_software(db: Session = Depends(get_db)):
    """返回全部软件，预置软件排在前面。"""
    rows = db.query(Software).order_by(Software.id.asc()).all()
    return [software_payload(row) for row in rows]


@router.post("/parse")
def parse(body: ParseRequest, db: Session = Depends(get_db)):
    """从用户输入里提炼软件名称。"""
    return parse_query(db, body.query)


@router.get("/software/{slug}/versions")
def versions(slug: str, platform: str = "windows", db: Session = Depends(get_db)):
    """返回某个软件的版本列表。"""
    return list_versions(db, slug, platform)


@router.post("/plans")
def create_plan(body: PlanRequest, db: Session = Depends(get_db)):
    """获取或生成一份安装方案。"""
    plan = get_or_create_plan(db, body.slug, body.version, body.platform)
    return plan_payload(db, plan)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """读取一份已经生成的方案。"""
    from app.models import Plan

    plan = db.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="没有这个方案")
    return plan_payload(db, plan)


@router.post("/plans/{plan_id}/feedback")
def create_feedback(plan_id: int, body: FeedbackRequest, db: Session = Depends(get_db)):
    """提交方案有效或无效的反馈。"""
    row = add_feedback(db, plan_id, body.verdict, body.content)
    return _feedback_payload(db, row)


def _feedback_payload(db: Session, row: Feedback) -> dict:
    """组装反馈响应。"""
    return {
        "id": row.id,
        "planId": row.plan_id,
        "verdict": row.verdict,
        "content": row.content,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
    }
