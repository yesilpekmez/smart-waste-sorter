"""Ayırma kararı: yazılım kuralları geçilirse işlem kontrol servisine devredilir."""
from __future__ import annotations

from typing import Optional

from flask import current_app

from .control import controller, sync_bins
from .models import Bin, Detection, Operation, db


def rejection_reason(detection: Detection, bin_: Bin) -> Optional[str]:
    if detection.confidence < current_app.config["MIN_CONFIDENCE"]:
        return "uncertain"
    if bin_.fill >= current_app.config["FULL_THRESHOLD"]:
        return "bin_full"
    return None


def sort(detection: Detection) -> Operation:
    """Kuralları uygular ve ayırmayı başlatır.

    Kontrol servisi meşgul ya da arızalıysa ControllerFault fırlatır; bu durumda
    işlem kaydı oluşturulmaz.
    """
    sync_bins()
    reason = rejection_reason(detection, db.session.get(Bin, detection.label))

    if reason:
        status = "rejected"
    else:
        result = controller().sort(detection.label)
        status = "completed" if result.ok else "failed"
        reason = result.error_code
        sync_bins()

    op = Operation(detection_id=detection.id, target_bin=detection.label, status=status, reason=reason)
    db.session.add(op)
    db.session.commit()
    return op
