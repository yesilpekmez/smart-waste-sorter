"""Ayırma kararı ve simüle edilmiş kontrol servisi.

Gerçek sistemde platformu döndürme ve servoyu bırakma işini controller/
modülü yapacak; burada yalnızca sonucunu (doluluk artışı) taklit ediyoruz.
"""
from __future__ import annotations

import random
from typing import Optional

from flask import current_app

from .models import Bin, Detection, Operation, db


def rejection_reason(detection: Detection, bin_: Bin) -> Optional[str]:
    if detection.confidence < current_app.config["MIN_CONFIDENCE"]:
        return "uncertain"
    if bin_.fill >= current_app.config["FULL_THRESHOLD"]:
        return "bin_full"
    return None


def sort(detection: Detection) -> Operation:
    bin_ = db.session.get(Bin, detection.label)
    reason = rejection_reason(detection, bin_)

    if reason is None:
        bin_.fill = min(100, bin_.fill + random.randint(3, 7))

    op = Operation(
        detection_id=detection.id,
        target_bin=detection.label,
        status="rejected" if reason else "completed",
        reason=reason,
    )
    db.session.add(op)
    db.session.commit()
    return op
