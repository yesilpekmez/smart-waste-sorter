import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from controller import ControllerFault, SortController, State  # noqa: E402
from controller.hardware import fill_percent  # noqa: E402
from controller.simulated import SimulatedHardware, SimulatedWorld  # noqa: E402


class FakeClock:
    """sleep çağrıldıkça ilerleyen sahte saat; testler beklemeden çalışır."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def hw():
    return SimulatedHardware(SimulatedWorld(time_scale=0))


@pytest.fixture
def ctrl(hw):
    clock = FakeClock()
    return SortController(hw, clock=clock, sleep=clock.sleep)


def test_successful_sort_drops_item_and_returns_home(hw, ctrl):
    hw.place_item()
    result = ctrl.sort("glass")

    assert result.ok
    assert [s for s, _ in result.trace] == ["routing", "dropping", "verifying", "returning", "idle"]
    assert not hw.world.item_on_platform
    assert hw.world.levels["glass"] > 0
    assert ctrl.fill_levels()["glass"] > 0
    assert hw.platform.at_reference()


def test_no_item_is_not_a_fault(hw, ctrl):
    result = ctrl.sort("paper")
    assert (result.ok, result.error_code) == (False, "no_item")
    assert ctrl.state == State.IDLE


def test_jam_triggers_safe_stop(hw, ctrl):
    hw.place_item()
    hw.world.faults.add("jam")

    result = ctrl.sort("metal")
    assert result.error_code == "jam"
    assert ctrl.state == State.FAULT

    # Arıza giderilmeden yeni ayırma kabul edilmez
    with pytest.raises(ControllerFault) as err:
        ctrl.sort("metal")
    assert err.value.code == "faulted"


def test_position_error_stops_before_dropping(hw, ctrl):
    hw.place_item()
    hw.world.faults.add("position")

    result = ctrl.sort("paper")
    assert result.error_code == "position_error"
    assert hw.world.item_on_platform  # atık yanlış bölmeye düşmedi
    assert sum(hw.world.levels.values()) == 0


def test_reset_recovers_from_fault(hw, ctrl):
    hw.place_item()
    hw.world.faults.add("jam")
    ctrl.sort("plastic")

    hw.world.faults.clear()
    ctrl.reset()
    assert ctrl.state == State.IDLE
    assert ctrl.sort("plastic").ok


def test_fill_percent_conversion():
    assert fill_percent(30) == 0
    assert fill_percent(5) == 100
    assert fill_percent(17.5) == 50
    assert fill_percent(40) == 0  # sensör sapması sınırlanır
    assert fill_percent(2) == 100


def test_set_fill_round_trips(hw, ctrl):
    hw.set_fill("metal", 82)
    assert ctrl.fill_levels()["metal"] == 82


def fast_controller(hw):
    from controller import Timeouts

    return SortController(hw, timeouts=Timeouts(move=0.2, home=0.2, gate=0.2, drop=0.2, stop=0.2))


def test_unexpected_driver_error_becomes_fault(hw):
    ctrl = fast_controller(hw)
    stopped = []
    original_stop = hw.platform.stop
    hw.platform.stop = lambda: (stopped.append(True), original_stop())
    hw.place_item()
    hw.world.faults.add("gate_error")

    result = ctrl.sort("glass")
    assert (result.ok, result.fault, result.error_code) == (False, True, "driver_error")
    assert "OSError" in result.error
    assert ctrl.state == State.FAULT
    assert stopped, "motor durdurulmalı"


def test_failing_safe_stop_still_ends_in_fault(hw):
    ctrl = fast_controller(hw)
    hw.place_item()
    hw.world.faults.update({"gate_error", "stop_error"})

    result = ctrl.sort("glass")
    assert ctrl.state == State.FAULT
    assert "motor durdurulamadı" in result.error


def test_stalled_motor_times_out(hw):
    ctrl = fast_controller(hw)
    hw.place_item()
    hw.world.faults.add("stall")

    result = ctrl.sort("metal")
    assert result.error_code == "timeout"
    assert ctrl.state == State.FAULT
    assert hw.world.item_on_platform


def test_failed_reset_keeps_fault(hw):
    ctrl = fast_controller(hw)
    hw.place_item()
    hw.world.faults.add("jam")
    ctrl.sort("paper")

    hw.world.faults = {"home"}
    with pytest.raises(ControllerFault) as err:
        ctrl.reset()
    assert err.value.code == "home_error"
    assert ctrl.state == State.FAULT


def test_no_item_result_is_not_a_fault(hw, ctrl):
    result = ctrl.sort("paper")
    assert result.fault is False
    assert ctrl.fault is None


def test_initialize_starts_in_fault_when_homing_fails(hw):
    hw.world.faults.add("home")
    ctrl = fast_controller(hw)
    ctrl.initialize()
    assert ctrl.state == State.FAULT
