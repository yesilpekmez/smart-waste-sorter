"""Backend ile kontrol yazılımı (controller/) arasındaki bağlantı."""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, current_app

# controller/ paketi depo kökünde duruyor
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from controller import SortController  # noqa: E402
from controller.simulated import SimulatedHardware, SimulatedWorld  # noqa: E402

from .models import Bin, db  # noqa: E402

# Simülasyonun başlangıç doluluk değerleri
DEMO_FILL = {"plastic": 42, "paper": 28, "glass": 65, "metal": 82}


def create_controller(app: Flask) -> SortController:
    if app.config["HARDWARE"] != "simulated":
        raise NotImplementedError("Raspberry Pi sürücüleri henüz yazılmadı")
    hw = SimulatedHardware(SimulatedWorld(time_scale=app.config["SIM_TIME_SCALE"]))
    for bin_type, percent in DEMO_FILL.items():
        hw.set_fill(bin_type, percent)
    return SortController(hw)


def controller() -> SortController:
    return current_app.extensions["controller"]


def simulator():
    """Simülasyon modundaysa donanım nesnesini, değilse None döndürür."""
    hw = controller().hw
    return hw if isinstance(hw, SimulatedHardware) else None


def sync_bins() -> list:
    """Doluluk sensörlerini okuyup veritabanındaki bölme kayıtlarını günceller."""
    bins = []
    for bin_type, fill in controller().fill_levels().items():
        bin_ = db.session.get(Bin, bin_type) or Bin(type=bin_type)
        bin_.fill = fill
        db.session.add(bin_)
        bins.append(bin_)
    db.session.commit()
    return bins
