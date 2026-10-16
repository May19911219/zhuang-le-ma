import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AdminSession, Feedback, Plan, SelectionStat, Software, utcnow
from app.schemas import FeedbackStatusRequest, LoginRequest, PlanUpdateRequest
from app.services.plans import get_or_create_plan, plan_payload, software_payload

router = APIRouter(prefix="/api/admin")


def require_admin(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AdminSession:
    """校验管理后台登录令牌。"""
    token = authorization.removeprefix("Bearer ").strip()
    row = db.query(AdminSession).filter(AdminSession.token == token).one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="请先登录")
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise HTTPException(status_code=401, detail="登录已过期")
    return row


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """用管理密码换取登录令牌。"""
    if not secrets.compare_digest(body.password, get_settings().admin_password):
        raise HTTPException(status_code=401, detail="密码不对")
    token = secrets.token_urlsafe(32)
    db.add(AdminSession(token=token, expires_at=utcnow() + timedelta(days=7)))
    db.commit()
    return {"token": token}


@router.get("/plans")
def list_plans(_: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    """列出全部安装方案。"""
    rows = db.query(Plan).order_by(Plan.updated_at.desc()).all()
    return [plan_payload(db, row) for row in rows]


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    body: PlanUpdateRequest,
    _: AdminSession = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """修改方案的 Markdown 和脚本。"""
    plan = db.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="没有这个方案")
    plan.markdown = body.markdown
    plan.script = body.script
    plan.updated_at = utcnow()
    db.commit()
    db.refresh(plan)
    return plan_payload(db, plan)


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, _: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    """删除一份安装方案及其反馈。"""
    plan = db.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="没有这个方案")
    db.query(Feedback).filter(Feedback.plan_id == plan.id).delete()
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.post("/plans/{plan_id}/regenerate")
def regenerate_plan(plan_id: int, _: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    """让 AI 按原软件、版本和平台重新生成方案。"""
    plan = db.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="没有这个方案")
    software = db.query(Software).filter(Software.id == plan.software_id).one()
    updated = get_or_create_plan(db, software.slug, plan.version, plan.platform, force_ai=True)
    return plan_payload(db, updated)


@router.get("/feedback")
def list_feedback(_: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    """列出用户反馈。"""
    rows = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    result = []
    for row in rows:
        plan = db.query(Plan).filter(Plan.id == row.plan_id).one_or_none()
        software_name = ""
        version = ""
        platform = ""
        if plan:
            software = db.query(Software).filter(Software.id == plan.software_id).one_or_none()
            software_name = software.name if software else ""
            version = plan.version
            platform = plan.platform
        result.append(
            {
                "id": row.id,
                "planId": row.plan_id,
                "softwareName": software_name,
                "version": version,
                "platform": platform,
                "verdict": row.verdict,
                "content": row.content,
                "status": row.status,
                "createdAt": row.created_at.isoformat(),
            }
        )
    return result


@router.patch("/feedback/{feedback_id}")
def update_feedback(
    feedback_id: int,
    body: FeedbackStatusRequest,
    _: AdminSession = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """把反馈标记为已处理或未处理。"""
    if body.status not in {"pending", "resolved"}:
        raise HTTPException(status_code=400, detail="状态只能是 pending 或 resolved")
    row = db.query(Feedback).filter(Feedback.id == feedback_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="没有这条反馈")
    row.status = body.status
    db.commit()
    return {"id": row.id, "status": row.status}


@router.get("/stats")
def stats(_: AdminSession = Depends(require_admin), db: Session = Depends(get_db)):
    """返回软件、版本、平台的选择次数。"""
    rows = db.query(SelectionStat).order_by(SelectionStat.count.desc()).all()
    result = []
    for row in rows:
        software = db.query(Software).filter(Software.id == row.software_id).one_or_none()
        result.append(
            {
                "software": software_payload(software) if software else None,
                "version": row.version,
                "platform": row.platform,
                "count": row.count,
            }
        )
    return result
