"""Donanım arayüzleri ve fiziksel ölçüler."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# Döner platformun her bölme için durması gereken açı (derece)
BIN_ANGLES = {"plastic": 0, "paper": 90, "glass": 180, "metal": 270}

# Mesafe sensörünün bölme boşken ve doluyken ölçtüğü mesafe (cm)
EMPTY_DISTANCE_CM = 30.0
FULL_DISTANCE_CM = 5.0


class Platform(Protocol):
    """Step motorla dönen platform."""

    def rotate_to(self, angle: float) -> None: ...

    def position(self) -> float: ...

    def home(self) -> None:
        """Referans sensörü görülene kadar döner ve açıyı sıfırlar."""

    def at_reference(self) -> bool: ...

    def stop(self) -> None: ...


class Gate(Protocol):
    """Atığı bölmeye bırakan servo kapak."""

    def open(self) -> None: ...

    def close(self) -> None: ...


class PresenceSensor(Protocol):
    """Kızılötesi sensör: platform üzerinde atık var mı?"""

    def item_present(self) -> bool: ...


class DistanceSensor(Protocol):
    """Bölmenin üstündeki ultrasonik sensör."""

    def distance_cm(self) -> float: ...


@dataclass
class Hardware:
    platform: Platform
    gate: Gate
    presence: PresenceSensor
    fill_sensors: dict  # bölme türü -> DistanceSensor


def fill_percent(distance_cm: float) -> int:
    """Ölçülen mesafeyi doluluk yüzdesine çevirir."""
    ratio = (EMPTY_DISTANCE_CM - distance_cm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)
    return round(min(1.0, max(0.0, ratio)) * 100)
