"""Ayırma durum makinesi.

    IDLE → ROUTING → DROPPING → VERIFYING → RETURNING → IDLE
                 ↘         ↘          ↘           ↘
                              FAULT (güvenli durdurma)

Arıza durumunda kapak kapatılır, motor durdurulur ve reset() çağrılana kadar
yeni ayırma kabul edilmez.
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .hardware import BIN_ANGLES, Hardware, fill_percent

POSITION_TOLERANCE_DEG = 2.0
DROP_TIMEOUT_S = 2.0
POLL_INTERVAL_S = 0.05


class State(str, enum.Enum):
    IDLE = "idle"
    ROUTING = "routing"
    DROPPING = "dropping"
    VERIFYING = "verifying"
    RETURNING = "returning"
    FAULT = "fault"


class ControllerFault(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class SortResult:
    ok: bool
    target_bin: str
    error_code: Optional[str] = None
    error: Optional[str] = None
    # (durum, başlangıçtan geçen saniye) çiftleri
    trace: list = field(default_factory=list)


class SortController:
    def __init__(self, hardware: Hardware, clock: Callable[[], float] = time.monotonic, sleep=time.sleep):
        self.hw = hardware
        self.clock = clock
        self.sleep = sleep
        self.state = State.IDLE
        self.fault: Optional[ControllerFault] = None
        self._lock = threading.Lock()

    # Durum sorguları

    def fill_levels(self) -> dict:
        return {t: fill_percent(s.distance_cm()) for t, s in self.hw.fill_sensors.items()}

    def item_present(self) -> bool:
        return self.hw.presence.item_present()

    def status(self) -> dict:
        return {
            "state": self.state.value,
            "fault": None if self.fault is None else {"code": self.fault.code, "message": self.fault.message},
        }

    # Komutlar

    def sort(self, target_bin: str) -> SortResult:
        if target_bin not in BIN_ANGLES:
            raise ValueError(f"Bilinmeyen bölme: {target_bin}")
        if not self._lock.acquire(blocking=False):
            raise ControllerFault("busy", "Başka bir ayırma işlemi sürüyor")
        try:
            if self.state == State.FAULT:
                raise ControllerFault("faulted", "Sistem arıza durumunda; önce sıfırlanmalı")
            return self._run(target_bin)
        finally:
            self._lock.release()

    def reset(self) -> None:
        """Arızadan sonra platformu referansa döndürür ve sistemi hazır duruma getirir."""
        with self._lock:
            self.hw.gate.close()
            self.hw.platform.home()
            if not self.hw.platform.at_reference():
                raise ControllerFault("home_error", "Platform referans konumuna dönemedi")
            self.fault = None
            self.state = State.IDLE

    # İç akış

    def _run(self, target_bin: str) -> SortResult:
        start = self.clock()
        trace = []

        def enter(state: State) -> None:
            self.state = state
            trace.append((state.value, round(self.clock() - start, 3)))

        try:
            if not self.hw.presence.item_present():
                raise ControllerFault("no_item", "Platformda atık yok")

            enter(State.ROUTING)
            angle = BIN_ANGLES[target_bin]
            self.hw.platform.rotate_to(angle)
            if abs(self.hw.platform.position() - angle) > POSITION_TOLERANCE_DEG:
                raise ControllerFault("position_error", "Platform hedef açıya ulaşamadı")

            enter(State.DROPPING)
            self.hw.gate.open()
            dropped = self._wait_until(lambda: not self.hw.presence.item_present(), DROP_TIMEOUT_S)
            self.hw.gate.close()

            enter(State.VERIFYING)
            if not dropped:
                raise ControllerFault("jam", "Atık platformdan ayrılmadı (sıkışma)")

            enter(State.RETURNING)
            self.hw.platform.home()
            if not self.hw.platform.at_reference():
                raise ControllerFault("home_error", "Platform referans konumuna dönemedi")

            enter(State.IDLE)
            return SortResult(ok=True, target_bin=target_bin, trace=trace)

        except ControllerFault as fault:
            if fault.code == "no_item":
                return SortResult(False, target_bin, fault.code, fault.message, trace)
            self._safe_stop(fault)
            enter(State.FAULT)
            return SortResult(False, target_bin, fault.code, fault.message, trace)

    def _safe_stop(self, fault: ControllerFault) -> None:
        self.fault = fault
        try:
            self.hw.gate.close()
        finally:
            self.hw.platform.stop()

    def _wait_until(self, condition: Callable[[], bool], timeout: float) -> bool:
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if condition():
                return True
            self.sleep(POLL_INTERVAL_S)
        return condition()
