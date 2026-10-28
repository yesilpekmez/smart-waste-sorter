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
    ctrl = SortController(hw)
    ctrl.initialize()  # açılışta referans konumu aranır
    return ctrl


def controller() -> SortController:
    return current_app.extensions["controller"]


def simulator():
    """Simülasyon modundaysa donanım nesnesini, değilse None döndürür."""
    hw = controller().hw
    return hw if isinstance(hw, SimulatedHardware) else None


def sync_bins() -> dict:
    """Doluluk sensörlerini okur; okunabilenleri veritabanına yazar.

    Bölme türü → yaklaşık doluluk yüzdesi döndürür. Sensörü okunamayan bölme
    için değer None olur; veritabanında son bilinen değer kalır.
    """
    levels = controller().fill_levels()
    for bin_type, fill in levels.items():
        if fill is None:
            continue
        bin_ = db.session.get(Bin, bin_type) or Bin(type=bin_type)
        bin_.fill = fill
        db.session.add(bin_)
    db.session.commit()
    return levels


def bin_payload(bin_type: str, levels: dict) -> dict:
    """Bölmenin anlık okumasını, son başarılı okumanın zamanıyla birlikte döndürür."""
    bin_ = db.session.get(Bin, bin_type)
    return {
        "type": bin_type,
        "fill": levels.get(bin_type),
        "sensorOk": levels.get(bin_type) is not None,
        "updatedAt": bin_.to_dict()["updatedAt"] if bin_ else None,
    }
