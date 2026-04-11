"""检修域 MVP 业务服务（工单状态机、检索快照、回填、审批、升级等）。"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.models.mvp_domain import (
    Annotation,
    ApprovalTask,
    AuditLog,
    AuthUser,
    Device,
    Escalation,
    FlowTemplate,
    KnowledgeArticle,
    MvpAttachment,
    RetrievalSnapshot,
    Role,
    SystemConfig,
    UserRole,
    WorkOrder,
    WorkOrderEvent,
    WorkOrderFilling,
    WorkOrderFillingAttachment,
    WorkOrderMessage,
)
from app.modules.mvp_maintenance.datetime_util import to_iso_cn
from app.modules.mvp_maintenance.deps import CurrentUserCtx
from app.modules.mvp_maintenance.errors import MaintenanceAPIError
from app.modules.mvp_maintenance.security import create_access_token, hash_password, verify_password
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.knowledge_service import KnowledgeService

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _map_maint_for_knowledge(ml: str | None) -> str:
    if not ml:
        return "standard"
    s = ml.strip()
    if any(x in s for x in ("抢修", "应急")):
        return "emergency"
    if any(x in s for x in ("日常", "保养")):
        return "routine"
    return "standard"


def _wo_public(wo: WorkOrder) -> dict[str, Any]:
    return {
        "id": wo.id,
        "device_id": wo.device_id,
        "status": wo.status,
        "maintenance_level": wo.maintenance_level,
        "flow_template_id": wo.flow_template_id,
        "current_step_no": wo.current_step_no,
        "last_retrieval_snapshot_id": wo.last_retrieval_snapshot_id,
        "created_by_user_id": wo.created_by_user_id,
        "created_at": to_iso_cn(wo.created_at),
        "updated_at": to_iso_cn(wo.updated_at),
    }


def _can_read_wo(ctx: CurrentUserCtx, wo: WorkOrder) -> bool:
    if ctx.has_any("admin", "expert", "safety"):
        return True
    return wo.created_by_user_id == ctx.user_id


class MVPMaintenanceService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def _audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_user_id: int | None,
        payload: dict | None = None,
        business_code: str | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                actor_user_id=actor_user_id,
                payload=payload,
                business_code=business_code,
                created_at=datetime.now(timezone.utc),
            )
        )

    async def login(self, username: str, password: str) -> dict[str, Any]:
        result = await self.session.execute(
            select(AuthUser).options(selectinload(AuthUser.roles)).where(AuthUser.username == username)
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise MaintenanceAPIError(401, "INVALID_CREDENTIALS", "用户名或密码错误")
        if not user.is_active:
            raise MaintenanceAPIError(401, "INVALID_CREDENTIALS", "用户已禁用")
        roles = [r.code for r in user.roles]
        token = create_access_token(
            secret=self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
            user_id=user.id,
            username=user.username,
            roles=roles,
            expires_minutes=self.settings.access_token_expire_minutes,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "roles": roles,
            },
        }

    async def get_me(self, ctx: CurrentUserCtx) -> dict[str, Any]:
        result = await self.session.execute(
            select(AuthUser).options(selectinload(AuthUser.roles)).where(AuthUser.id == ctx.user_id)
        )
        user = result.scalar_one()
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "roles": [r.code for r in user.roles],
        }

    async def list_devices(
        self,
        *,
        page: int,
        page_size: int,
        device_type: str | None,
        model: str | None,
        q: str | None,
    ) -> dict[str, Any]:
        stmt = select(Device)
        if device_type:
            stmt = stmt.where(Device.device_type == device_type)
        if model:
            stmt = stmt.where(Device.model.contains(model))
        if q:
            stmt = stmt.where(
                (Device.asset_code.contains(q)) | (Device.model.contains(q)) | (Device.location.contains(q))
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": d.id,
                "device_type": d.device_type,
                "model": d.model,
                "asset_code": d.asset_code,
                "location": d.location,
                "responsibility_expert_user_id": d.responsibility_expert_user_id,
                "created_at": to_iso_cn(d.created_at),
                "updated_at": to_iso_cn(d.updated_at),
            }
            for d in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_device(self, device_id: int) -> Device:
        d = await self.session.get(Device, device_id)
        if d is None:
            raise MaintenanceAPIError(404, "DEVICE_NOT_FOUND", "设备不存在")
        return d

    async def patch_device(self, device_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        d = await self.get_device(device_id)
        if "location" in body and body["location"] is not None:
            d.location = body["location"]
        if "responsibility_expert_user_id" in body:
            d.responsibility_expert_user_id = body["responsibility_expert_user_id"]
        d.updated_at = datetime.now(timezone.utc)
        await self._audit(
            "DEVICE_UPDATED",
            "device",
            str(device_id),
            ctx.user_id,
            {"fields": list(body.keys())},
        )
        await self.session.commit()
        return {
            "id": d.id,
            "device_type": d.device_type,
            "model": d.model,
            "asset_code": d.asset_code,
            "location": d.location,
            "responsibility_expert_user_id": d.responsibility_expert_user_id,
            "created_at": to_iso_cn(d.created_at),
            "updated_at": to_iso_cn(d.updated_at),
        }

    async def create_device(self, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        d = Device(
            device_type=body["device_type"],
            model=body["model"],
            asset_code=body.get("asset_code"),
            location=body.get("location"),
            responsibility_expert_user_id=body.get("responsibility_expert_user_id"),
            extra=body.get("extra"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(d)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise MaintenanceAPIError(409, "DUPLICATE_ASSET", "资产编号冲突") from e
        await self._audit("DEVICE_CREATED", "device", str(d.id), ctx.user_id, None)
        await self.session.commit()
        await self.session.refresh(d)
        return {
            "id": d.id,
            "device_type": d.device_type,
            "model": d.model,
            "asset_code": d.asset_code,
            "location": d.location,
            "responsibility_expert_user_id": d.responsibility_expert_user_id,
            "created_at": to_iso_cn(d.created_at),
            "updated_at": to_iso_cn(d.updated_at),
        }

    def _upload_dir(self) -> Path:
        p = Path(self.settings.maintenance_upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _sign_attachment_token(self, attachment_id: int, exp: int) -> str:
        msg = f"{attachment_id}:{exp}"
        sig = hmac.new(
            self.settings.attachment_sign_secret.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{msg}:{sig}"

    def _verify_attachment_token(self, token: str) -> tuple[int, int]:
        parts = token.split(":")
        if len(parts) != 3:
            raise MaintenanceAPIError(403, "FORBIDDEN", "签名无效")
        aid_s, exp_s, sig = parts
        aid, exp = int(aid_s), int(exp_s)
        expect = self._sign_attachment_token(aid, exp)
        if not hmac.compare_digest(token, expect):
            raise MaintenanceAPIError(403, "FORBIDDEN", "签名无效")
        if int(datetime.now(timezone.utc).timestamp()) > exp:
            raise MaintenanceAPIError(403, "FORBIDDEN", "链接已过期")
        return aid, exp

    async def save_attachment(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime: str,
        biz_type: str,
        work_order_id: int | None,
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise MaintenanceAPIError(
                413,
                "PAYLOAD_TOO_LARGE",
                "单文件超过 10MB 限制",
                data=None,
            )
        uid = uuid.uuid4().hex
        key = f"{ctx.user_id}/{uid}_{filename}"
        path = self._upload_dir() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        att = MvpAttachment(
            work_order_id=work_order_id,
            biz_type=biz_type,
            storage_key=key,
            mime_type=mime,
            size_bytes=len(file_bytes),
            uploaded_by_user_id=ctx.user_id,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(att)
        await self.session.commit()
        await self.session.refresh(att)
        return {
            "id": att.id,
            "work_order_id": att.work_order_id,
            "biz_type": att.biz_type,
            "mime_type": att.mime_type,
            "size_bytes": att.size_bytes,
            "created_at": to_iso_cn(att.created_at),
        }

    async def get_attachment_for_download(self, attachment_id: int, ctx: CurrentUserCtx) -> MvpAttachment:
        att = await self.session.get(MvpAttachment, attachment_id)
        if att is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "附件不存在")
        if att.uploaded_by_user_id != ctx.user_id and not ctx.has_any("admin", "expert", "safety"):
            # 绑定工单的附件：创建人/管理员可读
            if att.work_order_id:
                wo = await self.session.get(WorkOrder, att.work_order_id)
                if wo and not _can_read_wo(ctx, wo):
                    raise MaintenanceAPIError(403, "FORBIDDEN", "无权下载该附件")
        return att

    async def attachment_file_path(self, attachment_id: int) -> tuple[MvpAttachment, Path]:
        att = await self.session.get(MvpAttachment, attachment_id)
        if att is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "附件不存在")
        path = self._upload_dir() / att.storage_key
        if not path.is_file():
            raise MaintenanceAPIError(404, "NOT_FOUND", "文件已丢失")
        return att, path

    async def _get_wo(self, work_order_id: int) -> WorkOrder:
        wo = await self.session.get(WorkOrder, work_order_id)
        if wo is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "工单不存在")
        return wo

    async def _assert_wo_readable(self, ctx: CurrentUserCtx, wo: WorkOrder) -> None:
        if not _can_read_wo(ctx, wo):
            raise MaintenanceAPIError(404, "NOT_FOUND", "工单不存在")

    async def _transition(
        self,
        wo: WorkOrder,
        to_status: str,
        *,
        event_type: str,
        actor_user_id: int | None,
        payload: dict | None = None,
    ) -> None:
        ev = WorkOrderEvent(
            work_order_id=wo.id,
            from_status=wo.status,
            to_status=to_status,
            event_type=event_type,
            payload=payload,
            actor_user_id=actor_user_id,
            created_at=datetime.now(timezone.utc),
        )
        wo.status = to_status
        wo.updated_at = datetime.now(timezone.utc)
        self.session.add(ev)

    async def create_work_order(self, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        if "device_id" not in body or body["device_id"] is None:
            raise MaintenanceAPIError(
                400,
                "VALIDATION_ERROR",
                "device_id 必填",
                errors=[{"field": "device_id", "code": "REQUIRED", "message": "必填"}],
            )
        await self.get_device(int(body["device_id"]))
        wo = WorkOrder(
            device_id=int(body["device_id"]),
            status="S1",
            maintenance_level=body.get("maintenance_level"),
            created_by_user_id=ctx.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(wo)
        await self.session.flush()
        self.session.add(
            WorkOrderEvent(
                work_order_id=wo.id,
                from_status=None,
                to_status="S1",
                event_type="work_order_created",
                payload=None,
                actor_user_id=ctx.user_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        await self.session.commit()
        await self.session.refresh(wo)
        return _wo_public(wo)

    async def list_work_orders(
        self,
        ctx: CurrentUserCtx,
        *,
        page: int,
        page_size: int,
        status: str | None,
        device_id: int | None,
        mine: bool | None,
    ) -> dict[str, Any]:
        stmt = select(WorkOrder)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        if device_id:
            stmt = stmt.where(WorkOrder.device_id == device_id)
        if mine or (not ctx.has_any("admin", "expert", "safety")):
            stmt = stmt.where(WorkOrder.created_by_user_id == ctx.user_id)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(WorkOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return {
            "items": [_wo_public(w) for w in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_work_order_detail(self, work_order_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        return _wo_public(wo)

    async def list_events(self, work_order_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        stmt = (
            select(WorkOrderEvent)
            .where(WorkOrderEvent.work_order_id == work_order_id)
            .order_by(WorkOrderEvent.id.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": e.id,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "event_type": e.event_type,
                "payload": e.payload,
                "actor_user_id": e.actor_user_id,
                "created_at": to_iso_cn(e.created_at),
            }
            for e in rows
        ]
        n = len(items)
        return {"items": items, "total": n, "page": 1, "page_size": max(n, 1)}

    async def post_retrieval(
        self,
        work_order_id: int,
        body: dict[str, Any],
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if wo.status == "S1":
            await self._transition(wo, "S2", event_type="retrieval_started", actor_user_id=ctx.user_id)
        device = await self.get_device(wo.device_id)
        qtext = (body.get("query_text") or "").strip()
        ml = body.get("maintenance_level") or wo.maintenance_level
        ks = _map_maint_for_knowledge(ml if isinstance(ml, str) else None)

        kreq = KnowledgeSearchRequest(
            query=qtext or "检修",
            equipment_type=device.device_type,
            equipment_model=device.model,
            maintenance_level=ks,
            limit=8,
        )
        ksvc = KnowledgeService(self.session)
        soft_code: str | None = None
        soft_msg: str | None = None
        try:
            payload = await ksvc.search_multimodal(kreq)
            results = payload.get("results") or []
        except Exception:
            results = []
            soft_code = "MODEL_UNAVAILABLE"
            soft_msg = "检索或模型链路异常，已降级为片段模式"

        citations: list[dict[str, Any]] = []
        chunks_json: list[dict[str, Any]] = []
        top_score = None
        for r in results[:8]:
            cid = int(r["chunk_id"])
            excerpt = (r.get("excerpt") or "")[:800]
            src = r.get("source_name") or r.get("title") or ""
            citations.append(
                {
                    "chunk_id": cid,
                    "source_document": src,
                    "excerpt": excerpt,
                }
            )
            chunks_json.append(
                {
                    "chunk_id": cid,
                    "source_document": src,
                    "score": r.get("score"),
                    "text_excerpt": excerpt,
                }
            )
            if top_score is None and r.get("score") is not None:
                top_score = float(r["score"])

        empty_hit = len(citations) == 0
        if empty_hit and soft_code is None:
            soft_code = "EMPTY_HIT"
            soft_msg = "未命中可用知识片段，请补充描述或发起升级"

        device_snap = {
            "device_id": device.id,
            "model": device.model,
            "asset_code": device.asset_code,
            "device_type": device.device_type,
        }
        snap = RetrievalSnapshot(
            work_order_id=wo.id,
            query_text=qtext,
            chunks=chunks_json,
            model_name=None,
            knowledge_corpus_version=None,
            confidence_top1=top_score,
            empty_hit=empty_hit,
            degraded_response=True,
            prompt_template_version="mvp-1",
            device_context_snapshot=device_snap,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(snap)
        await self.session.flush()

        # 建议正文：拼接出处以满足 FR-RAG-004 可自动化规则
        if citations:
            suggested = "建议参考：" + "；".join(
                f"{c['source_document']}（chunk_id={c['chunk_id']}）" for c in citations[:5]
            )
        else:
            suggested = soft_msg or "暂无检索结果。"

        msg = WorkOrderMessage(
            work_order_id=wo.id,
            role="assistant",
            content=suggested,
            retrieval_snapshot_id=snap.id,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(msg)
        wo.last_retrieval_snapshot_id = snap.id
        if wo.status == "S2":
            await self._transition(wo, "S3", event_type="retrieval_done", actor_user_id=ctx.user_id)
        await self._audit(
            "retrieval.completed",
            "work_order",
            str(wo.id),
            ctx.user_id,
            {"retrieval_snapshot_id": snap.id, "empty_hit": empty_hit},
            business_code=soft_code,
        )
        await self.session.commit()
        await self.session.refresh(msg)
        await self.session.refresh(snap)

        base_data = {
            "retrieval_snapshot_id": snap.id,
            "message_id": msg.id,
            "suggested_reply": suggested,
            "citations": citations,
            "work_order": _wo_public(wo),
        }
        if soft_code:
            return {
                "http": 200,
                "success": False,
                "business_code": soft_code,
                "message": soft_msg or "",
                "data": {
                    **base_data,
                    "empty_hit": empty_hit,
                },
            }
        return {"http": 200, "success": True, "business_code": None, "message": None, "data": base_data}

    async def post_user_message(
        self,
        work_order_id: int,
        body: dict[str, Any],
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        msg = WorkOrderMessage(
            work_order_id=wo.id,
            role="user",
            content=body["content"],
            retrieval_snapshot_id=None,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return {"id": msg.id, "created_at": to_iso_cn(msg.created_at)}

    async def list_messages(
        self,
        work_order_id: int,
        ctx: CurrentUserCtx,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        stmt = select(WorkOrderMessage).where(WorkOrderMessage.work_order_id == work_order_id)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = (
            stmt.order_by(WorkOrderMessage.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "retrieval_snapshot_id": m.retrieval_snapshot_id,
                "created_at": to_iso_cn(m.created_at),
            }
            for m in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def action_enter_maintenance(self, work_order_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if wo.status not in ("S3", "S5"):
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "当前状态不允许进入检修")
        # 绑定已发布模板
        device = await self.get_device(wo.device_id)
        ft_stmt = select(FlowTemplate).where(
            FlowTemplate.device_type == device.device_type,
            FlowTemplate.maintenance_level == (wo.maintenance_level or "计划定修"),
            FlowTemplate.status == "published",
        )
        ft = (await self.session.execute(ft_stmt)).scalar_one_or_none()
        if ft:
            wo.flow_template_id = ft.id
            wo.current_step_no = 1
        await self._transition(wo, "S7", event_type="enter_maintenance", actor_user_id=ctx.user_id)
        await self.session.commit()
        return {"work_order": _wo_public(wo)}

    async def action_complete_maintenance(self, work_order_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if wo.status != "S7":
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "仅检修中可完成检修")
        await self._transition(wo, "S8", event_type="complete_maintenance", actor_user_id=ctx.user_id)
        await self.session.commit()
        return {"work_order": _wo_public(wo)}

    async def action_accept_fill_review(self, work_order_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("expert", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅专家或管理员可复核")
        wo = await self._get_wo(work_order_id)
        if wo.status != "S9":
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "工单不在待验收状态")
        await self._transition(wo, "S10", event_type="expert_accept_fill", actor_user_id=ctx.user_id)
        await self.session.commit()
        return {"work_order": _wo_public(wo)}

    def _validate_filling(self, body: dict[str, Any]) -> None:
        rs = body.get("resolution_status")
        cc = body.get("closure_code")
        att = body.get("attachment_ids") or []
        if rs not in ("resolved", "unresolved"):
            raise MaintenanceAPIError(
                400,
                "VALIDATION_ERROR",
                "resolution_status 非法",
                errors=[{"field": "resolution_status", "code": "INVALID_ENUM", "message": ""}],
            )
        if not isinstance(att, list) or len(att) < 1:
            raise MaintenanceAPIError(
                400,
                "VALIDATION_ERROR",
                "attachment_ids 至少 1 个",
                errors=[{"field": "attachment_ids", "code": "REQUIRED", "message": ""}],
            )
        if rs == "resolved":
            allowed = {"NORMAL", "PART_REPLACED", "ADJUSTED", "OTHER"}
            if cc not in allowed:
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "closure_code 非法")
            if cc == "OTHER" and not (body.get("detail_notes") or "").strip():
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "OTHER 须填写 detail_notes")
        else:
            if cc != "UNRESOLVED":
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "unresolved 时 closure_code 须为 UNRESOLVED")
            pua = body.get("post_unresolved_action")
            if pua not in ("REOPEN_ESCALATION", "RETRY_RETRIEVAL", "CLOSE_UNRESOLVED"):
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "post_unresolved_action 必填且枚举合法")
            urc = body.get("unresolved_reason_code")
            allowed_ur = {
                "EQUIPMENT_LIMIT",
                "INFO_INSUFFICIENT",
                "EXPERT_REQUIRED",
                "USER_ABORT",
                "OTHER",
            }
            if urc not in allowed_ur:
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "unresolved_reason_code 非法")
            if urc == "OTHER" and not (body.get("detail_notes") or "").strip():
                raise MaintenanceAPIError(400, "VALIDATION_ERROR", "OTHER 原因须填写 detail_notes")

    async def post_filling(self, work_order_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if wo.status != "S8":
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "仅待回填状态可提交")
        self._validate_filling(body)
        await self.session.execute(
            update(WorkOrderFilling)
            .where(
                WorkOrderFilling.work_order_id == wo.id,
                WorkOrderFilling.is_latest.is_(True),
            )
            .values(is_latest=False)
        )
        fill = WorkOrderFilling(
            work_order_id=wo.id,
            is_latest=True,
            resolution_status=body["resolution_status"],
            closure_code=body["closure_code"],
            post_unresolved_action=body.get("post_unresolved_action"),
            unresolved_reason_code=body.get("unresolved_reason_code"),
            detail_notes=body.get("detail_notes"),
            submitted_by_user_id=ctx.user_id,
            submitted_at=datetime.now(timezone.utc),
        )
        self.session.add(fill)
        await self.session.flush()
        for aid in body["attachment_ids"]:
            self.session.add(
                WorkOrderFillingAttachment(filling_id=fill.id, attachment_id=int(aid)),
            )
        await self._transition(wo, "S9", event_type="fill_submitted", actor_user_id=ctx.user_id)
        await self._audit("filling.submitted", "work_order", str(wo.id), ctx.user_id, {"filling_id": fill.id})
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise MaintenanceAPIError(
                409,
                "INVALID_STATE_TRANSITION",
                "并发回填冲突，请重试",
            ) from None
        return {"work_order": _wo_public(wo), "filling_id": fill.id}

    async def list_approval_tasks(self, ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("safety", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅审批人可查看")
        stmt = select(ApprovalTask).where(ApprovalTask.status == "pending").order_by(ApprovalTask.id.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": t.id,
                "work_order_id": t.work_order_id,
                "step_no": t.step_no,
                "status": t.status,
                "created_at": to_iso_cn(t.created_at),
            }
            for t in rows
        ]
        n = len(items)
        return {"items": items, "total": n, "page": 1, "page_size": max(n, 1)}

    async def resolve_approval(
        self,
        approval_task_id: int,
        body: dict[str, Any],
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        if not ctx.has_any("safety", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅审批人可操作")
        t = await self.session.get(ApprovalTask, approval_task_id)
        if t is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "审批任务不存在")
        new_status = body["status"]
        if new_status not in ("approved", "rejected", "need_more_info"):
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "status 非法")
        wo = await self._get_wo(t.work_order_id)
        # 终态幂等须先于「工单须在 S6」校验（首包通过后工单已离开 S6）
        if t.status != "pending":
            if t.status == new_status:
                await self._audit(
                    "approval.idempotent",
                    "approval_task",
                    str(t.id),
                    ctx.user_id,
                    {"note": "duplicate"},
                    business_code="ALREADY_PROCESSED",
                )
                await self.session.commit()
                return {
                    "id": t.id,
                    "work_order_id": t.work_order_id,
                    "status": t.status,
                    "resolved_at": to_iso_cn(t.resolved_at),
                    "work_order": _wo_public(wo),
                    "business_code": "ALREADY_PROCESSED",
                }
            raise MaintenanceAPIError(409, "CONFLICT", "审批已终态且结论不一致")

        if wo.status != "S6":
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "工单不在待审批状态")

        t.status = new_status
        t.resolution = new_status
        t.comment = body.get("comment")
        t.material_attachment_ids = body.get("material_attachment_ids")
        t.approver_user_id = ctx.user_id
        t.resolved_at = datetime.now(timezone.utc)
        t.updated_at = datetime.now(timezone.utc)

        if new_status == "approved":
            await self._transition(wo, "S7", event_type="approval_approved", actor_user_id=ctx.user_id)
        elif new_status == "rejected":
            await self._transition(wo, "SX", event_type="approval_rejected", actor_user_id=ctx.user_id)
        else:
            await self._transition(wo, "S6", event_type="approval_need_info", actor_user_id=ctx.user_id)

        await self._audit("approval.resolve", "approval_task", str(t.id), ctx.user_id, {"status": new_status})
        await self.session.commit()
        await self.session.refresh(wo)
        return {
            "id": t.id,
            "work_order_id": t.work_order_id,
            "status": t.status,
            "resolved_at": to_iso_cn(t.resolved_at),
            "work_order": _wo_public(wo),
        }

    async def create_escalation(self, work_order_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        note = (body.get("escalation_note") or "").strip()
        if len(note) < 10:
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "escalation_note 至少 10 字")
        device = await self.get_device(wo.device_id)
        if device.responsibility_expert_user_id is None:
            raise MaintenanceAPIError(400, "EXPERT_NOT_CONFIGURED", "设备未配置责任专家")
        active_esc = (
            await self.session.execute(
                select(Escalation).where(
                    Escalation.work_order_id == wo.id,
                    Escalation.status.in_(["open", "in_progress"]),
                )
            )
        ).scalars().first()
        if active_esc is not None:
            raise MaintenanceAPIError(409, "ESCALATION_IN_PROGRESS", "已存在进行中的升级单")
        if wo.status not in ("S2", "S3"):
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "当前状态不可发起升级")
        rel_mid = body.get("related_message_id")
        if rel_mid is not None:
            m = await self.session.get(WorkOrderMessage, int(rel_mid))
            if m is None or m.work_order_id != wo.id or m.role != "assistant":
                raise MaintenanceAPIError(400, "INVALID_MESSAGE_REF", "related_message_id 非法")
        esc = Escalation(
            work_order_id=wo.id,
            status="open",
            assigned_expert_user_id=device.responsibility_expert_user_id,
            escalation_note=note,
            attachment_ids=body.get("attachment_ids"),
            related_message_id=rel_mid,
            created_by_user_id=ctx.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(esc)
        try:
            await self._transition(wo, "S4", event_type="escalation_created", actor_user_id=ctx.user_id)
            await self.session.flush()
            await self._audit("escalation.created", "work_order", str(wo.id), ctx.user_id, {"escalation_id": esc.id})
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise MaintenanceAPIError(409, "ESCALATION_IN_PROGRESS", "已存在进行中的升级单") from None
        await self.session.refresh(esc)
        return {"id": esc.id, "work_order_id": wo.id, "status": esc.status, "work_order": _wo_public(wo)}

    async def get_escalation(self, escalation_id: int, ctx: CurrentUserCtx) -> dict[str, Any]:
        esc = await self.session.get(Escalation, escalation_id)
        if esc is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "升级单不存在")
        wo = await self._get_wo(esc.work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if ctx.has_any("expert") and esc.assigned_expert_user_id != ctx.user_id and not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "非指派专家不可查看")
        return {
            "id": esc.id,
            "work_order_id": esc.work_order_id,
            "status": esc.status,
            "assigned_expert_user_id": esc.assigned_expert_user_id,
            "escalation_note": esc.escalation_note,
            "conclusion_text": esc.conclusion_text,
        }

    async def resolve_escalation(
        self,
        escalation_id: int,
        body: dict[str, Any],
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        esc = await self.session.get(Escalation, escalation_id)
        if esc is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "升级单不存在")
        if esc.assigned_expert_user_id != ctx.user_id and not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "非指派专家不可处理")
        wo = await self._get_wo(esc.work_order_id)
        if wo.status not in ("S4", "S5"):
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "工单状态不允许会诊结论")
        conclusion = (body.get("conclusion_text") or "").strip()
        if not conclusion:
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "conclusion_text 必填")
        high_risk = bool(body.get("requires_high_risk_work"))
        esc.status = "resolved"
        esc.conclusion_text = conclusion
        esc.resolved_at = datetime.now(timezone.utc)
        esc.updated_at = datetime.now(timezone.utc)
        if high_risk:
            await self._transition(wo, "S6", event_type="escalation_high_risk", actor_user_id=ctx.user_id)
            # 创建待审批任务（绑定当前工步）
            step_no = wo.current_step_no or 2
            self.session.add(
                ApprovalTask(
                    work_order_id=wo.id,
                    step_no=step_no,
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        else:
            await self._transition(wo, "S7", event_type="escalation_resolved", actor_user_id=ctx.user_id)
        await self._audit(
            "escalation.resolved",
            "escalation",
            str(esc.id),
            ctx.user_id,
            {"high_risk": high_risk, "work_order_id": wo.id},
        )
        await self.session.commit()
        await self.session.refresh(wo)
        return {"id": esc.id, "status": esc.status, "work_order": _wo_public(wo)}

    async def list_flow_templates(self, device_type: str | None, maintenance_level: str | None) -> dict[str, Any]:
        stmt = select(FlowTemplate).where(FlowTemplate.status == "published")
        if device_type:
            stmt = stmt.where(FlowTemplate.device_type == device_type)
        if maintenance_level:
            stmt = stmt.where(FlowTemplate.maintenance_level == maintenance_level)
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": ft.id,
                "name": ft.name,
                "device_type": ft.device_type,
                "maintenance_level": ft.maintenance_level,
                "version": ft.version,
            }
            for ft in rows
        ]
        n = len(items)
        return {"items": items, "total": n, "page": 1, "page_size": max(n, 1)}

    async def get_flow_template(self, template_id: int) -> dict[str, Any]:
        ft = await self.session.get(FlowTemplate, template_id)
        if ft is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "模板不存在")
        return {
            "id": ft.id,
            "name": ft.name,
            "device_type": ft.device_type,
            "maintenance_level": ft.maintenance_level,
            "steps_json": ft.steps_json,
            "version": ft.version,
            "status": ft.status,
        }

    async def confirm_step(self, work_order_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        wo = await self._get_wo(work_order_id)
        await self._assert_wo_readable(ctx, wo)
        if wo.status != "S7":
            raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "工单不在检修中")
        if not body.get("mark_done", True):
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "mark_done 须为 true")
        step_no = int(body["step_no"])
        if wo.flow_template_id is None:
            raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "未绑定流程模板")
        ft = await self.session.get(FlowTemplate, wo.flow_template_id)
        if ft is None:
            raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "模板不存在")
        steps = ft.steps_json if isinstance(ft.steps_json, list) else []
        step_def = next((s for s in steps if int(s.get("step_no", -1)) == step_no), None)
        if step_def is None:
            raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "工步不在模板中")
        progress = dict(wo.step_progress_json or {})
        done_list = list(progress.get("completed_steps", []))
        if step_no in done_list:
            await self._audit(
                "step.confirm.idempotent",
                "work_order",
                str(wo.id),
                ctx.user_id,
                {"step_no": step_no},
                business_code="ALREADY_PROCESSED",
            )
            await self.session.commit()
            return {
                "work_order_id": wo.id,
                "current_step_no": wo.current_step_no,
                "confirmed_step_no": step_no,
                "business_code": "ALREADY_PROCESSED",
            }
        if wo.current_step_no is None or step_no != wo.current_step_no:
            raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "工步序号不匹配")
        if step_def.get("requires_approval"):
            stmt = select(ApprovalTask).where(
                ApprovalTask.work_order_id == wo.id,
                ApprovalTask.step_no == step_no,
                ApprovalTask.status == "approved",
            )
            ok = (await self.session.execute(stmt)).scalar_one_or_none()
            if ok is None:
                raise MaintenanceAPIError(409, "STEP_NOT_ALLOWED", "高危工步未审批通过")
        done_list.append(step_no)
        progress["completed_steps"] = done_list
        wo.step_progress_json = progress
        next_no = step_no + 1
        if any(int(s.get("step_no", -1)) == next_no for s in steps):
            wo.current_step_no = next_no
        else:
            wo.current_step_no = next_no
        wo.updated_at = datetime.now(timezone.utc)
        await self._audit("step.confirmed", "work_order", str(wo.id), ctx.user_id, {"step_no": step_no})
        await self.session.commit()
        return {
            "work_order_id": wo.id,
            "current_step_no": wo.current_step_no,
            "confirmed_step_no": step_no,
        }

    async def create_annotation(
        self,
        work_order_id: int,
        message_id: int,
        body: dict[str, Any],
        ctx: CurrentUserCtx,
    ) -> dict[str, Any]:
        if not ctx.has_any("expert", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅专家可标注")
        wo = await self._get_wo(work_order_id)
        m = await self.session.get(WorkOrderMessage, message_id)
        if m is None or m.work_order_id != wo.id:
            raise MaintenanceAPIError(404, "NOT_FOUND", "消息不存在")
        ann = Annotation(
            work_order_id=wo.id,
            message_id=m.id,
            annotator_user_id=ctx.user_id,
            label=body["label"],
            comment=body.get("comment"),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(ann)
        await self._audit(
            "annotation.created",
            "work_order_message",
            str(m.id),
            ctx.user_id,
            {"annotation_label": body["label"], "work_order_id": wo.id},
        )
        await self.session.commit()
        await self.session.refresh(ann)
        return {"id": ann.id}

    async def spawn_kb_draft(self, annotation_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("expert", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅专家可操作")
        ann = await self.session.get(Annotation, annotation_id)
        if ann is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "标注不存在")
        if ann.candidate_kb_patch_id:
            return {
                "knowledge_article_id": ann.candidate_kb_patch_id,
                "status": "draft",
                "source_annotation_id": ann.id,
                "business_code": "ALREADY_PROCESSED",
            }
        title = (body or {}).get("title_hint") or "知识修订草稿"
        ka = KnowledgeArticle(
            series_id=0,
            title=title,
            body="（由标注生成的草稿，请专家完善）",
            status="draft",
            version=1,
            source_work_order_id=ann.work_order_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(ka)
        await self.session.flush()
        ka.series_id = ka.id
        ann.candidate_kb_patch_id = ka.id
        await self.session.commit()
        return {
            "knowledge_article_id": ka.id,
            "status": "draft",
            "source_annotation_id": ann.id,
        }

    async def kb_from_work_order(self, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("expert", "admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "权限不足")
        wo = await self._get_wo(int(body["work_order_id"]))
        if wo.status != "S10":
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "工单须已结单")
        ka = KnowledgeArticle(
            series_id=0,
            title=body.get("title") or f"工单{wo.id}沉淀",
            body=body.get("body") or "待完善",
            status="draft",
            version=1,
            source_work_order_id=wo.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(ka)
        await self.session.flush()
        ka.series_id = ka.id
        await self.session.commit()
        return {"id": ka.id, "status": ka.status, "series_id": ka.series_id}

    async def list_kb_articles(self, ctx: CurrentUserCtx, status: str | None, page: int, page_size: int) -> dict[str, Any]:
        stmt = select(KnowledgeArticle)
        if status:
            stmt = stmt.where(KnowledgeArticle.status == status)
        if not ctx.has_any("admin", "expert"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "无权查看知识列表")
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(KnowledgeArticle.id.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": r.id,
                "series_id": r.series_id,
                "title": r.title,
                "status": r.status,
                "version": r.version,
            }
            for r in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def review_kb(self, article_id: int, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("expert"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅专家可审核")
        ka = await self.session.get(KnowledgeArticle, article_id)
        if ka is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "条目不存在")
        if ka.status not in ("pending_review", "draft"):
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "状态不允许审核")
        action = body["action"]
        if action == "reject" and not (body.get("comment") or "").strip():
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "驳回须填写意见")
        if action == "request_revise" and not (body.get("comment") or "").strip():
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "须填写修订说明")
        if action == "approve":
            ka.status = "pending_publish"
        elif action == "reject":
            ka.status = "rejected_review"
        else:
            ka.status = "pending_review"
        ka.reviewer_expert_user_id = ctx.user_id
        ka.updated_at = datetime.now(timezone.utc)
        await self._audit("kb.review", "knowledge_article", str(ka.id), ctx.user_id, {"action": action})
        await self.session.commit()
        return {"id": ka.id, "status": ka.status, "reviewed_at": to_iso_cn(ka.updated_at)}

    async def publish_kb(self, article_id: int, body: dict[str, Any] | None, ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅管理员可发布")
        ka = await self.session.get(KnowledgeArticle, article_id)
        if ka is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "条目不存在")
        if ka.status not in ("pending_publish",):
            raise MaintenanceAPIError(409, "INVALID_STATE_TRANSITION", "当前状态不可发布")
        try:
            ka.status = "published"
            ka.publisher_admin_user_id = ctx.user_id
            ka.published_at = datetime.now(timezone.utc)
            ka.updated_at = datetime.now(timezone.utc)
            await self._audit("kb.publish", "knowledge_article", str(ka.id), ctx.user_id, {"series_id": ka.series_id})
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise MaintenanceAPIError(409, "SERIES_PUBLISHED_CONFLICT", "同系列已存在已发布版本") from None
        return {
            "id": ka.id,
            "status": ka.status,
            "series_id": ka.series_id,
            "published_at": to_iso_cn(ka.published_at),
        }

    async def list_audit_logs(
        self,
        ctx: CurrentUserCtx,
        *,
        page: int,
        page_size: int,
        resource_type: str | None,
        resource_id: str | None,
    ) -> dict[str, Any]:
        if not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅管理员可查审计")
        stmt = select(AuditLog)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if resource_id:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": x.id,
                "action": x.action,
                "actor_user_id": x.actor_user_id,
                "resource_type": x.resource_type,
                "resource_id": x.resource_id,
                "payload": x.payload,
                "created_at": to_iso_cn(x.created_at),
            }
            for x in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def list_system_configs(self, ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅管理员")
        rows = (await self.session.execute(select(SystemConfig))).scalars().all()
        items = []
        for c in rows:
            entry: dict[str, Any] = {
                "key": c.key,
                "value_type": c.value_type,
                "reload_policy": c.reload_policy,
                "is_sensitive": c.is_sensitive,
                "updated_at": to_iso_cn(c.updated_at),
            }
            if c.is_sensitive:
                entry["value_masked"] = "****"
            else:
                entry["value"] = c.value
            items.append(entry)
        n = len(items)
        return {"items": items, "total": n, "page": 1, "page_size": max(n, 1)}

    async def patch_system_config(self, key: str, body: dict[str, Any], ctx: CurrentUserCtx) -> dict[str, Any]:
        if not ctx.has_any("admin"):
            raise MaintenanceAPIError(403, "FORBIDDEN", "仅管理员")
        c = await self.session.get(SystemConfig, key)
        if c is None:
            raise MaintenanceAPIError(404, "NOT_FOUND", "配置不存在")
        if c.is_sensitive:
            raise MaintenanceAPIError(400, "VALIDATION_ERROR", "敏感配置不可通过接口写入")
        c.value = body.get("value", c.value)
        c.updated_at = datetime.now(timezone.utc)
        c.updated_by_user_id = ctx.user_id
        await self.session.commit()
        return {
            "key": c.key,
            "value": c.value,
            "value_type": c.value_type,
            "reload_policy": c.reload_policy,
            "is_sensitive": c.is_sensitive,
            "updated_at": to_iso_cn(c.updated_at),
        }

    async def admin_list_users(self, page: int, page_size: int) -> dict[str, Any]:
        stmt = select(AuthUser).options(selectinload(AuthUser.roles))
        total = (await self.session.execute(select(func.count()).select_from(AuthUser))).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        items = [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "is_active": u.is_active,
                "roles": [r.code for r in u.roles],
            }
            for u in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def admin_create_user(self, body: dict[str, Any]) -> dict[str, Any]:
        u = AuthUser(
            username=body["username"],
            password_hash=hash_password(body["password"]),
            display_name=body.get("display_name") or body["username"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(u)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise MaintenanceAPIError(409, "DUPLICATE_USERNAME", "用户名已存在") from None
        for code in body.get("role_codes", []):
            r = (
                await self.session.execute(select(Role).where(Role.code == code))
            ).scalar_one_or_none()
            if r:
                self.session.add(UserRole(user_id=u.id, role_id=r.id))
        await self.session.commit()
        return {"id": u.id, "username": u.username}

    async def admin_assign_roles(self, user_id: int, body: dict[str, Any]) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for code in body.get("role_codes", []):
            r = (
                await self.session.execute(select(Role).where(Role.code == code))
            ).scalar_one_or_none()
            if r:
                self.session.add(UserRole(user_id=user_id, role_id=r.id))
        await self.session.commit()

    async def health_sub(self) -> dict[str, Any]:
        from app.core.database import check_database_connection

        return {
            "app": "ok",
            "database": "ok" if await check_database_connection() else "error",
            "vector": "skipped",
            "llm": "config_only",
        }
