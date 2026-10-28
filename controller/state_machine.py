"""Ayırma durum makinesi.

    IDLE → ROUTING → DROPPING → VERIFYING → RETURNING → IDLE
                 ↘         ↘          ↘           ↘
                              FAULT (güvenli durdurma)

Arıza durumunda motor durdurulur, kapak kapatılır ve reset() başarılı olana
kadar yeni ayırma kabul edilmez. Durdurma adımlarının kendisi başarısız olsa
bile sistem arıza durumunda kalır.

Sürücülerden gelen her hata (ControllerFault dışındakiler de) ve zaman aşımına
uğrayan her hareket arızaya dönüştürülür.

Arıza, ayırmayı yürüten iş parçacığının dışında da oluşabilir (ör. panelin
atık sensörü okuması). Bu durumda arıza kaydedilir ve çıkışlar durdurulur;
ayırma her hareketten önce ve sonra arızayı denetlediği için yeni hareket
başlatmaz. Denetim ile hareketin başlatılması aynı kilit altındadır.

Doluluk sensörleri hareketi etkilemez: okunamayan bölmenin doluluğu "bilinmiyor"
(None) döner ve sistemi arızaya sokmaz; o bölmeye ayırma yapılıp yapılmayacağına
backend karar verir.
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
# Doluluk sensörü çağrılarının etiket öneki; bunlar sıfırlamayı engellemez
FILL_LABEL = "Doluluk: "


@dataclass
class Timeouts:
    """Her donanım adımı için izin verilen en uzun süre (saniye)."""

    move: float = 5.0  # platformun hedef açıya dönmesi
    home: float = 8.0  # referans sensörüne dönüş
    gate: float = 2.0  # servonun açılması ya da kapanması
    drop: float = 2.0  # atığın platformdan ayrılması
    sensor: float = 1.0  # sensör okuma süresi
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
        # Ayırma ve sıfırlama komutlarının sahipliği
        self._lock = threading.Lock()
        # Arıza/durum değişiklikleri ve sürücü iş parçacıklarının kaydı
        self._workers_lock = threading.Lock()
        self._workers: dict[str, threading.Thread] = {}
        self._call_locks: dict[str, threading.Lock] = {}

    # Durum sorguları

    def fill_levels(self) -> dict:
        """Bölme türü → yaklaşık doluluk yüzdesi; okunamayan sensör için None."""
        levels = {}
        for bin_type, sensor in self.hw.fill_sensors.items():
            try:
                levels[bin_type] = fill_percent(self._call(sensor.distance_cm, self.timeouts.sensor, FILL_LABEL + bin_type))
            except Exception:
                levels[bin_type] = None
        return levels

    def item_present(self) -> bool:
        """Atık sensörünü okur. Sensör hata verirse arıza kaydedilir ve çıkışlar durdurulur."""
        try:
            return self._call(self.hw.presence.item_present, self.timeouts.sensor, "Atık sensörü")
        except Exception as exc:
            fault = self._as_fault(exc)
            self._safe_stop(fault)
            raise self.fault

    def status(self) -> dict:
        with self._workers_lock:
            fault, state = self.fault, self.state
        return {
            "state": state.value,
            "fault": None if fault is None else {"code": fault.code, "message": fault.message},
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
            if self.fault is not None:
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
            with self._workers_lock:
                pending = any(
                    worker.is_alive() for label, worker in self._workers.items() if not label.startswith(FILL_LABEL)
                )
            if pending:
                # Asıl arıza nedeni korunur; yalnızca sıfırlama reddedilir
                raise ControllerFault("busy", "Önceki sürücü komutu henüz durmadı; sıfırlama engellendi")
        except ControllerFault:
            self._lock.release()
            raise
        try:
            self._call(self.hw.gate.close, self.timeouts.gate, "Kapağın kapanması")
            self._call(self.hw.platform.home, self.timeouts.home, "Referansa dönüş")
            if not self._call(self.hw.platform.at_reference, self.timeouts.sensor, "Referans sensörü"):
                raise ControllerFault("home_error", "Platform referans konumuna dönemedi")
        except Exception as exc:
            self._safe_stop(self._as_fault(exc), replace=True)
            raise self.fault
        else:
            with self._workers_lock:
                self.fault = None
                self.state = State.IDLE
        finally:
            self._lock.release()

    # İç akış

    def _run(self, target_bin: str) -> SortResult:
        start = self.clock()
        trace = []

        def enter(state: State) -> None:
            # Dışarıdan kaydedilen arızanın üzerine yazılmaz
            with self._workers_lock:
                if self.fault is not None:
                    raise self.fault
                self.state = state
            trace.append((state.value, round(self.clock() - start, 3)))

        def step(action, timeout, what):
            return self._call(action, timeout, what, guarded=True)

        def result(**kwargs) -> SortResult:
            return SortResult(target_bin=target_bin, trace=trace, duration_s=round(self.clock() - start, 3), **kwargs)

        try:
            if not step(self.hw.presence.item_present, self.timeouts.sensor, "Atık sensörü"):
                return result(ok=False, error_code="no_item", error="Platformda atık yok")

            enter(State.ROUTING)
            angle = BIN_ANGLES[target_bin]
            step(lambda: self.hw.platform.rotate_to(angle), self.timeouts.move, "Platformun dönmesi")
            if abs(step(self.hw.platform.position, self.timeouts.sensor, "Konum sensörü") - angle) > POSITION_TOLERANCE_DEG:
                raise ControllerFault("position_error", "Platform hedef açıya ulaşamadı")

            enter(State.DROPPING)
            step(self.hw.gate.open, self.timeouts.gate, "Kapağın açılması")
            dropped = self._wait_until(
                lambda: not step(self.hw.presence.item_present, self.timeouts.sensor, "Atık sensörü"),
                self.timeouts.drop,
            )
            step(self.hw.gate.close, self.timeouts.gate, "Kapağın kapanması")

            enter(State.VERIFYING)
            if not dropped:
                raise ControllerFault("jam", "Atık platformdan ayrılmadı (sıkışma)")

            enter(State.RETURNING)
            step(self.hw.platform.home, self.timeouts.home, "Referansa dönüş")
            if not step(self.hw.platform.at_reference, self.timeouts.sensor, "Referans sensörü"):
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

    def _safe_stop(self, fault: ControllerFault, replace: bool = False) -> None:
        """Arızayı kaydeder, motoru durdurur ve kapağı kapatır.

        Bir arıza olayında ilk neden korunur; sıfırlama gibi yeni bir denemenin
        başarısızlığı ise (replace=True) önceki kaydın yerine geçer. Durdurma
        adımları başarısız olsa da sistem arıza durumunda kalır. Hangi iş
        parçacığından çağrıldığı fark etmez.
        """
        with self._workers_lock:
            if self.fault is None or replace:
                self.fault = fault
            self.state = State.FAULT
        problems = []
        for action, label in ((self.hw.platform.stop, "motor durdurulamadı"), (self.hw.gate.close, "kapak kapatılamadı")):
            try:
                self._call(action, self.timeouts.stop, label)
            except Exception as exc:
                problems.append(f"{label}: {exc}")
        if problems:
            with self._workers_lock:
                self.fault = ControllerFault(self.fault.code, f"{self.fault.message} — ayrıca {'; '.join(problems)}")

    def _call(self, action: Callable[[], object], timeout: float, what: str, guarded: bool = False):
        """Sürücü komutunu ayrı iş parçacığında çalıştırır; süresi aşılırsa arıza verir.

        Python iş parçacığı zorla durdurulamaz; bu yüzden zaman aşımından sonra
        _safe_stop motoru durdurma komutu gönderir ve sürücünün bunu dinlemesi gerekir.

        guarded: ayırma adımları için. Kayıtlı bir arıza varsa komut başlatılmaz;
        komut sürerken arıza kaydedildiyse sonucu kullanılmaz.
        """
        outcome: dict = {}

        def target():
            try:
                outcome["value"] = action()
            except BaseException as exc:  # noqa: BLE001 — hata çağırana aktarılır
                outcome["error"] = exc

        worker = threading.Thread(target=target, daemon=True)
        with self._workers_lock:
            call_lock = self._call_locks.setdefault(what, threading.Lock())
        # Aynı sensörü panel ve kontrol akışı birlikte okuyabilir. Normal okumalar
        # sıraya girer; zaman aşımından kalan çağrı varken yeni sürücü başlatılmaz.
        if not call_lock.acquire(timeout=timeout):
            raise ControllerFault("timeout", f"Sürücü çağrısı bekleniyor: {what}")
        try:
            with self._workers_lock:
                previous = self._workers.get(what)
                if previous is not None and previous.is_alive():
                    raise ControllerFault("busy", f"Önceki sürücü çağrısı sürüyor: {what}")
                if guarded and self.fault is not None:
                    raise self.fault
                self._workers[what] = worker
                worker.start()
            worker.join(timeout)
            if worker.is_alive():
                raise ControllerFault("timeout", f"{what} {timeout:g} saniyede tamamlanmadı")
            if guarded:
                with self._workers_lock:
                    if self.fault is not None:
                        raise self.fault
            if "error" in outcome:
                raise outcome["error"]
            return outcome.get("value")
        finally:
            call_lock.release()

    def _wait_until(self, condition: Callable[[], bool], timeout: float) -> bool:
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            if condition():
                return True
            self.sleep(POLL_INTERVAL_S)
        return condition()
