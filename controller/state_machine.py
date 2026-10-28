"""Ayırma durum makinesi.

    IDLE → ROUTING → DROPPING → VERIFYING → RETURNING → IDLE
                 ↘         ↘          ↘           ↘
                              FAULT (güvenli durdurma)

Arıza durumunda motor durdurulur, kapak kapatılır ve reset() başarılı olana
kadar yeni ayırma kabul edilmez. Durdurma adımlarının kendisi başarısız olsa
bile sistem arıza durumunda kalır.

Sürücülerden gelen her hata (ControllerFault dışındakiler de) ve zaman aşımına
uğrayan her hareket arızaya dönüştürülür.
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .hardware import BIN_ANGLES, Hardware, fill_percent

POSITION_TOLERANCE_DEG = 2.0
POLL_INTERVAL_S = 0.05


@dataclass
class Timeouts:
    """Her donanım adımı için izin verilen en uzun süre (saniye)."""

    move: float = 5.0  # platformun hedef açıya dönmesi
    home: float = 8.0  # referans sensörüne dönüş
    gate: float = 2.0  # servonun açılması ya da kapanması
    drop: float = 2.0  # atığın platformdan ayrılması
    stop: float = 1.0  # güvenli durdurma komutları


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
    # Sonuç bir donanım arızası mı? ("Platformda atık yok" arıza değildir)
    fault: bool = False
    # (durum, başlangıçtan geçen saniye) çiftleri
    trace: list = field(default_factory=list)
    duration_s: float = 0.0


class SortController:
    def __init__(
        self,
        hardware: Hardware,
        clock: Callable[[], float] = time.monotonic,
        sleep=time.sleep,
        timeouts: Optional[Timeouts] = None,
    ):
        self.hw = hardware
        self.clock = clock
        self.sleep = sleep
        self.timeouts = timeouts or Timeouts()
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

    def initialize(self) -> None:
        """Açılışta platformu referansa götürür; başarısız olursa arıza durumunda başlar."""
        try:
            self.reset()
        except ControllerFault:
            pass

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
        """Platformu referansa döndürür; başarılı olursa sistemi hazır duruma getirir.

        Başarısız olursa arıza durumunda kalır ve ControllerFault fırlatır.
        """
        if not self._lock.acquire(blocking=False):
            raise ControllerFault("busy", "Başka bir işlem sürüyor")
        try:
            self._call(self.hw.gate.close, self.timeouts.gate, "Kapağın kapanması")
            self._call(self.hw.platform.home, self.timeouts.home, "Referansa dönüş")
            if not self.hw.platform.at_reference():
                raise ControllerFault("home_error", "Platform referans konumuna dönemedi")
        except Exception as exc:
            fault = self._as_fault(exc)
            self._safe_stop(fault)
            raise self.fault
        else:
            self.fault = None
            self.state = State.IDLE
        finally:
            self._lock.release()

    # İç akış

    def _run(self, target_bin: str) -> SortResult:
        start = self.clock()
        trace = []

        def enter(state: State) -> None:
            self.state = state
            trace.append((state.value, round(self.clock() - start, 3)))

        def result(**kwargs) -> SortResult:
            return SortResult(target_bin=target_bin, trace=trace, duration_s=round(self.clock() - start, 3), **kwargs)

        try:
            if not self.hw.presence.item_present():
                return result(ok=False, error_code="no_item", error="Platformda atık yok")

            enter(State.ROUTING)
            angle = BIN_ANGLES[target_bin]
            self._call(lambda: self.hw.platform.rotate_to(angle), self.timeouts.move, "Platformun dönmesi")
            if abs(self.hw.platform.position() - angle) > POSITION_TOLERANCE_DEG:
                raise ControllerFault("position_error", "Platform hedef açıya ulaşamadı")

            enter(State.DROPPING)
            self._call(self.hw.gate.open, self.timeouts.gate, "Kapağın açılması")
            dropped = self._wait_until(lambda: not self.hw.presence.item_present(), self.timeouts.drop)
            self._call(self.hw.gate.close, self.timeouts.gate, "Kapağın kapanması")

            enter(State.VERIFYING)
            if not dropped:
                raise ControllerFault("jam", "Atık platformdan ayrılmadı (sıkışma)")

            enter(State.RETURNING)
            self._call(self.hw.platform.home, self.timeouts.home, "Referansa dönüş")
            if not self.hw.platform.at_reference():
                raise ControllerFault("home_error", "Platform referans konumuna dönemedi")

            enter(State.IDLE)
            return result(ok=True)

        except Exception as exc:
            fault = self._as_fault(exc)
            self._safe_stop(fault)
            trace.append((State.FAULT.value, round(self.clock() - start, 3)))
            return result(ok=False, error_code=self.fault.code, error=self.fault.message, fault=True)

    @staticmethod
    def _as_fault(exc: Exception) -> ControllerFault:
        if isinstance(exc, ControllerFault):
            return exc
        return ControllerFault("driver_error", f"Beklenmeyen sürücü hatası: {type(exc).__name__}: {exc}")

    def _safe_stop(self, fault: ControllerFault) -> None:
        """Motoru durdurur ve kapağı kapatır; bunlar da başarısız olsa arıza durumunda kalır."""
        problems = []
        for action, label in ((self.hw.platform.stop, "motor durdurulamadı"), (self.hw.gate.close, "kapak kapatılamadı")):
            try:
                self._call(action, self.timeouts.stop, label)
            except Exception as exc:
                problems.append(f"{label}: {exc}")
        if problems:
            fault = ControllerFault(fault.code, f"{fault.message} — ayrıca {'; '.join(problems)}")
        self.fault = fault
        self.state = State.FAULT

    def _call(self, action: Callable[[], object], timeout: float, what: str):
        """Sürücü komutunu ayrı iş parçacığında çalıştırır; süresi aşılırsa arıza verir.

        Python iş parçacığı zorla durdurulamaz; bu yüzden zaman aşımından sonra
        _safe_stop motoru durdurma komutu gönderir ve sürücünün bunu dinlemesi gerekir.
        """
        outcome: dict = {}

        def target():
            try:
                outcome["value"] = action()
            except BaseException as exc:  # noqa: BLE001 — hata çağırana aktarılır
                outcome["error"] = exc

        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            raise ControllerFault("timeout", f"{what} {timeout:g} saniyede tamamlanmadı")
        if "error" in outcome:
            raise outcome["error"]
        return outcome.get("value")

    def _wait_until(self, condition: Callable[[], bool], timeout: float) -> bool:
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if condition():
                return True
            self.sleep(POLL_INTERVAL_S)
        return condition()
