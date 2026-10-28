"""Atık döngüsü ve ayırma akışı.

Platformdaki atık için yalnızca en son algılama geçerlidir: yeni bir algılama
geldiğinde öncekiler "eski" sayılır ve ayrılamaz. Her algılama en fazla bir
kez işlenir. Ayırma sürerken yeni algılama ve ikinci ayırma kabul edilmez.

İşlem kaydı hareket başlamadan "running" olarak yazılır ve sonuçla güncellenir;
böylece uygulama hareket sırasında kapanırsa yarım kalan işlem bilinir.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from flask import current_app
from sqlalchemy.exc import IntegrityError

from controller import ControllerFault, State

from .control import controller, sync_bins
from .models import Detection, Operation, db


class SortRefused(Exception):
    """İstek kabul edilmedi; işlem kaydı oluşturulmadı."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def running_operation() -> Optional[Operation]:
    return Operation.query.filter_by(status="running").first()


def latest_detection() -> Optional[Detection]:
    return Detection.query.order_by(Detection.id.desc()).first()


def rejection_reason(detection: Detection, fill: Optional[int]) -> Optional[str]:
    """fill: hedef bölmenin anlık doluluğu; sensör okunamadıysa None."""
    if detection.confidence < current_app.config["MIN_CONFIDENCE"]:
        return "uncertain"
    if fill is None:
        return "sensor_error"  # doluluk bilinmeden bölmeye atık gönderilmez
    if fill >= current_app.config["FULL_THRESHOLD"]:
        return "bin_full"
    return None


def refusal(detection: Detection) -> Optional[SortRefused]:
    """Algılama şu an ayrılamıyorsa nedenini döndürür."""
    if detection.operation is not None:
        return SortRefused("processed", "Bu atık zaten işlendi")
    if running_operation() is not None:
        return SortRefused("busy", "Başka bir ayırma işlemi sürüyor")
    if detection.id != latest_detection().id:
        return SortRefused("stale", "Bu tahmin artık geçerli değil; platformdaki atık için daha yeni bir algılama var")
    if controller().state == State.FAULT:
        return SortRefused("faulted", "Sistem arıza durumunda; önce sıfırlanmalı")
    return None


def sort(detection: Detection) -> Operation:
    refused = refusal(detection)
    if refused:
        raise refused

    reason = rejection_reason(detection, sync_bins()[detection.label])
    op = Operation(
        detection_id=detection.id,
        target_bin=detection.label,
        status="rejected" if reason else "running",
        reason=reason,
        min_confidence=current_app.config["MIN_CONFIDENCE"],
        full_threshold=current_app.config["FULL_THRESHOLD"],
        finished_at=_now() if reason else None,
    )
    db.session.add(op)
    try:
        db.session.commit()
    except IntegrityError:
        # Aynı algılama için eşzamanlı başka bir istek kaydı önce oluşturdu
        db.session.rollback()
        raise SortRefused("processed", "Bu atık zaten işleniyor")

    if reason:
        return op

    try:
        result = controller().sort(detection.label)
    except ControllerFault as fault:
        # Kontrol servisi hareketi hiç başlatmadı (meşgul ya da arızalı)
        db.session.delete(op)
        db.session.commit()
        raise SortRefused(fault.code, fault.message)

    if result.ok:
        op.status = "completed"
    elif result.fault:
        op.status = "failed"
    else:
        op.status = "aborted"
    op.reason = result.error_code
    op.message = result.error
    op.trace = json.dumps(result.trace)
    op.duration_ms = round(result.duration_s * 1000)
    op.finished_at = _now()
    db.session.commit()
    sync_bins()
    return op


def recover_interrupted() -> None:
    """Uygulama hareket sırasında kapandıysa yarım kalan işlemleri arıza olarak kapatır."""
    for op in Operation.query.filter_by(status="running").all():
        op.status = "failed"
        op.reason = "interrupted"
        op.message = "Uygulama ayırma sırasında kapandı"
        op.finished_at = _now()
    db.session.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)
