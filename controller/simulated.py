"""Donanım olmadan çalışan simülasyon sürücüleri.

Tüm sürücüler ortak bir SimulatedWorld nesnesini paylaşır: platformun açısı,
üzerinde atık olup olmadığı ve bölmelerin doluluk yüksekliği burada tutulur.
`faults` kümesine eklenerek arıza denenebilir:

    jam         atık platformdan düşmez
    position    motor adım kaçırır, platform hedef açıdan sapar
    home        platform referans sensörünü bulamaz
    stall       motor takılır; durdurma komutu gelene kadar hareket bitmez
    gate_error  servo sürücüsü OSError verir
    stop_error  motoru durdurma komutu da OSError verir
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .hardware import BIN_ANGLES, EMPTY_DISTANCE_CM, FULL_DISTANCE_CM, Hardware

DEGREES_PER_SECOND = 180.0
SERVO_SECONDS = 0.3
# Bir atığın bölmede kapladığı yükseklik aralığı (cm)
ITEM_HEIGHT_CM = (0.8, 1.8)


@dataclass
class SimulatedWorld:
    angle: float = 0.0
    item_on_platform: bool = False
    # Bölmedeki atık yığınının yüksekliği (cm)
    levels: dict = field(default_factory=lambda: {t: 0.0 for t in BIN_ANGLES})
    faults: set = field(default_factory=set)
    time_scale: float = 1.0  # testlerde 0

    def wait(self, seconds: float) -> None:
        if self.time_scale > 0:
            time.sleep(seconds * self.time_scale)

    def bin_under_platform(self) -> Optional[str]:
        return next((t for t, a in BIN_ANGLES.items() if abs(a - self.angle) < 1), None)


class SimulatedPlatform:
    def __init__(self, world: SimulatedWorld):
        self.world = world
        self._stopped = threading.Event()

    def rotate_to(self, angle: float) -> None:
        self._stopped.clear()
        if "stall" in self.world.faults:
            self._stopped.wait(30)  # durdurma komutuna kadar takılı kalır
            return
        delta = abs(angle - self.world.angle)
        duration = min(delta, 360 - delta) / DEGREES_PER_SECOND * max(0, self.world.time_scale)
        if self._stopped.wait(duration):
            return
        # Konum hatası: motor adım kaçırır
        self.world.angle = angle + (15 if "position" in self.world.faults else 0)

    def position(self) -> float:
        return self.world.angle

    def home(self) -> None:
        self.rotate_to(0)
        if "home" in self.world.faults:
            self.world.angle = 5

    def at_reference(self) -> bool:
        return abs(self.world.angle) < 1

    def stop(self) -> None:
        if "stop_error" in self.world.faults:
            raise OSError("Motor sürücüsüne yazılamadı")
        self._stopped.set()


class SimulatedGate:
    def __init__(self, world: SimulatedWorld):
        self.world = world

    def open(self) -> None:
        if "gate_error" in self.world.faults:
            raise OSError("Servo PWM kanalı açılamadı")
        self.world.wait(SERVO_SECONDS)
        target = self.world.bin_under_platform()
        if self.world.item_on_platform and "jam" not in self.world.faults and target:
            self.world.item_on_platform = False
            self.world.levels[target] += random.uniform(*ITEM_HEIGHT_CM)

    def close(self) -> None:
        self.world.wait(SERVO_SECONDS)


class SimulatedPresence:
    def __init__(self, world: SimulatedWorld):
        self.world = world

    def item_present(self) -> bool:
        return self.world.item_on_platform


class SimulatedDistance:
    def __init__(self, world: SimulatedWorld, bin_type: str):
        self.world = world
        self.bin_type = bin_type

    def distance_cm(self) -> float:
        level = self.world.levels[self.bin_type]
        return max(FULL_DISTANCE_CM - 1, EMPTY_DISTANCE_CM - level)


class SimulatedHardware(Hardware):
    def __init__(self, world: Optional[SimulatedWorld] = None):
        self.world = world or SimulatedWorld()
        super().__init__(
            platform=SimulatedPlatform(self.world),
            gate=SimulatedGate(self.world),
            presence=SimulatedPresence(self.world),
            fill_sensors={t: SimulatedDistance(self.world, t) for t in BIN_ANGLES},
        )

    # Simülasyona özel yardımcılar

    def place_item(self) -> None:
        """Platforma yeni atık konmuş gibi davranır."""
        self.world.item_on_platform = True

    def set_fill(self, bin_type: str, percent: float) -> None:
        self.world.levels[bin_type] = (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM) * percent / 100

    def empty_bin(self, bin_type: str) -> None:
        self.world.levels[bin_type] = 0.0
