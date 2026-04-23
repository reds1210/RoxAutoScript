from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from roxauto.emulator.adapter import AdbEmulatorAdapter
from roxauto.emulator.discovery import build_instance_state, find_adb_executable


SLOT_POINTS: list[tuple[str, tuple[int, int]]] = [
    ("slot_01_top_left", (110, 359)),
    ("slot_02_top_2", (279, 359)),
    ("slot_03_top_3", (478, 359)),
    ("slot_04_top_4", (677, 359)),
    ("slot_05_top_right", (845, 359)),
    ("slot_06_bottom_left", (110, 615)),
    ("slot_07_bottom_2", (279, 615)),
    ("slot_08_bottom_3", (478, 615)),
    ("slot_09_bottom_4", (677, 615)),
    ("slot_10_bottom_right", (845, 615)),
]
MATERIAL_SLOT_POINTS: list[tuple[str, tuple[int, int]]] = SLOT_POINTS[:-1]
CUSTOM_ORDER_SLOT = SLOT_POINTS[-1]

MAIN_SUBMIT_POINT = (1115, 606)
GET_BUTTON_CANDIDATES = (
    {
        "tap": (1157, 402),
        "samples": ((1128, 398), (1148, 405), (1168, 398)),
    },
)
BUY_NOW_POINT = (1126, 610)
BUY_CONFIRM_POINT = (652, 607)
BUY_CONFIRM_SAMPLE_POINTS = (
    (620, 607),
    (650, 607),
    (700, 607),
    (620, 590),
    (680, 590),
)
POPUP_SUBMIT_POINT = (919, 607)
CUSTOM_LIST_BUTTON_POINT = (1109, 672)
CUSTOM_LIST_BUTTON_SAMPLES = ((1062, 672), (1109, 652))
CUSTOM_LIST_PANEL_SUBMIT_POINT = (341, 627)
CUSTOM_LIST_PANEL_SAMPLES = ((318, 134), (319, 627))
CUSTOM_BACKPACK_GRID_COLUMNS = (740, 841, 942, 1043, 1144)
CUSTOM_BACKPACK_GRID_ROWS = (355, 457, 559, 661)
CUSTOM_BACKPACK_ITEM_POINTS = tuple(
    (column, row)
    for row in CUSTOM_BACKPACK_GRID_ROWS
    for column in CUSTOM_BACKPACK_GRID_COLUMNS
)
CUSTOM_QUANTITY_CONFIRM_POINT = (1051, 610)
CUSTOM_QUANTITY_CONFIRM_SAMPLES = ((1051, 610), (1051, 590))
CUSTOM_ORDER_SUBMITTED_SAMPLES = ((815, 478), (845, 478), (875, 478))


@dataclass(slots=True)
class ActionRecord:
    step_index: int
    action: str
    point: tuple[int, int] | None
    screenshot_path: str
    notes: str = ""


@dataclass(slots=True)
class CheckpointPollResult:
    screenshot_path: Path
    matched: bool
    attempt_count: int
    elapsed_sec: float


def _load_pillow_image():
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "run-guild-order-current-panel.py requires Pillow only when sampling screenshots; "
            "install Pillow to execute this helper."
        ) from exc
    return Image


def _pixel(path: Path, point: tuple[int, int]) -> tuple[int, int, int]:
    image_module = _load_pillow_image()
    with image_module.open(path) as image:
        rgb = image.convert("RGB")
        return tuple(int(channel) for channel in rgb.getpixel(point))


def _is_green_submit(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g >= 140 and g >= r + 20 and g >= b + 40


def _is_light_button(rgb: tuple[int, int, int]) -> bool:
    return min(rgb) >= 180


def _is_orange_buy_now(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r >= 170 and r >= g + 20 and g >= 90 and b <= 170


def _is_blue_buy(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return b >= 170 and b >= r + 35 and b >= g + 25


def _is_custom_list_button(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g >= 180 and r >= 110 and b <= 130


def _is_orange_button(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r >= 200 and g >= 140 and b <= 140


def _is_submitted_overlay(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g >= 90 and g >= r + 20 and g >= b + 20


def _resolve_custom_backpack_item_point(custom_order_index: int) -> tuple[int, int]:
    if custom_order_index < 1:
        raise ValueError("custom_order_index must be >= 1")
    if custom_order_index > len(CUSTOM_BACKPACK_ITEM_POINTS):
        raise ValueError(
            f"custom_order_index={custom_order_index} exceeds visible row-major range 1..{len(CUSTOM_BACKPACK_ITEM_POINTS)}"
        )
    return CUSTOM_BACKPACK_ITEM_POINTS[custom_order_index - 1]


def _poll_for_checkpoint(
    *,
    capture: Callable[[], Path],
    predicate: Callable[[Path], bool],
    initial_delay_sec: float,
    poll_interval_sec: float,
    timeout_sec: float,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> CheckpointPollResult:
    resolved_initial_delay = max(0.0, float(initial_delay_sec))
    resolved_poll_interval = max(0.05, float(poll_interval_sec))
    resolved_timeout = max(0.05, float(timeout_sec))
    start_monotonic = monotonic_fn()
    deadline = start_monotonic + resolved_timeout
    next_delay = resolved_initial_delay
    attempt_count = 0
    last_path: Path | None = None

    while True:
        if next_delay > 0.0:
            sleep_fn(next_delay)
        last_path = capture()
        attempt_count += 1
        if predicate(last_path):
            return CheckpointPollResult(
                screenshot_path=last_path,
                matched=True,
                attempt_count=attempt_count,
                elapsed_sec=max(0.0, monotonic_fn() - start_monotonic),
            )
        remaining = deadline - monotonic_fn()
        if remaining <= 0.0:
            return CheckpointPollResult(
                screenshot_path=last_path,
                matched=False,
                attempt_count=attempt_count,
                elapsed_sec=max(0.0, monotonic_fn() - start_monotonic),
            )
        next_delay = min(resolved_poll_interval, remaining)


class GuildOrderCurrentPanelRunner:
    def __init__(
        self,
        *,
        serial: str,
        output_root: Path,
        tap_delay_sec: float,
        poll_interval_sec: float,
        checkpoint_timeout_sec: float,
        max_material_actions: int,
        custom_order_index: int,
    ) -> None:
        adb_executable = find_adb_executable()
        if adb_executable is None:
            raise FileNotFoundError("adb executable not found")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._output_dir = output_root / f"guild-order-current-panel-{timestamp}"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._adapter = AdbEmulatorAdapter(
            adb_executable=adb_executable,
            screenshot_dir=self._output_dir,
        )
        self._instance = build_instance_state(serial)
        self._tap_delay_sec = tap_delay_sec
        self._poll_interval_sec = max(0.05, float(poll_interval_sec))
        self._checkpoint_timeout_sec = max(0.05, float(checkpoint_timeout_sec))
        self._max_material_actions = max_material_actions
        self._custom_order_index = int(custom_order_index)
        self._custom_order_point = _resolve_custom_backpack_item_point(self._custom_order_index)
        self._records: list[ActionRecord] = []
        self._step_index = 0

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def run(self) -> int:
        start_path = self._capture("start")
        self._record("capture", None, start_path, notes="manual current-panel start")

        completed_actions = 0
        while completed_actions < self._max_material_actions:
            progressed = self._scan_until_first_progress()
            if not progressed:
                break
            completed_actions += 1

        custom_order_processed = self._process_custom_order()

        end_path = self._capture("end")
        self._record(
            "capture",
            None,
            end_path,
            notes=(
                f"scan_complete completed_actions={completed_actions} "
                f"custom_order_processed={str(custom_order_processed).lower()} "
                f"custom_order_index={self._custom_order_index}"
            ),
        )
        self._write_report()
        return 0

    def _scan_until_first_progress(self) -> bool:
        for slot_name, point in MATERIAL_SLOT_POINTS:
            progressed = self._process_slot(slot_name, point)
            if progressed:
                return True
        return False

    def _process_slot(self, slot_name: str, point: tuple[int, int]) -> bool:
        selected_path = self._tap_and_capture(
            point,
            f"{slot_name}-selected",
            notes="select slot by text/hold region",
        )
        get_point = self._detect_get_button(selected_path)
        main_submit_rgb = _pixel(selected_path, MAIN_SUBMIT_POINT)

        if get_point is None:
            if _is_green_submit(main_submit_rgb):
                submitted_path = self._tap_and_capture(
                    MAIN_SUBMIT_POINT,
                    f"{slot_name}-after-main-submit",
                    notes="direct submit for sufficient material",
                    delay_sec=2.8,
                )
                self._record(
                    "submit_main",
                    MAIN_SUBMIT_POINT,
                    submitted_path,
                    notes=f"main_submit_rgb={main_submit_rgb}",
                )
                return True
            self._record(
                "skip_slot",
                point,
                selected_path,
                notes=f"no get button and no green submit; main_submit_rgb={main_submit_rgb}",
            )
            return False

        popup_path = self._tap_and_wait_for_checkpoint(
            get_point,
            f"{slot_name}-after-get",
            notes="open get/purchase popup",
            predicate=lambda screenshot_path: _is_orange_buy_now(_pixel(screenshot_path, BUY_NOW_POINT)),
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected orange buy-now popup after tapping get at {get_point}, "
                    f"got {_pixel(screenshot_path, BUY_NOW_POINT)}"
                )
            ),
        )
        buy_now_rgb = _pixel(popup_path, BUY_NOW_POINT)

        purchase_path = self._tap_and_wait_for_checkpoint(
            BUY_NOW_POINT,
            f"{slot_name}-after-buy-now",
            notes="open purchase panel",
            predicate=self._has_blue_buy_button,
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected blue purchase button after tapping buy-now, "
                    f"got center={_pixel(screenshot_path, BUY_CONFIRM_POINT)} "
                    f"samples={self._sample_pixels(screenshot_path, BUY_CONFIRM_SAMPLE_POINTS)}"
                )
            ),
        )
        buy_confirm_rgb = _pixel(purchase_path, BUY_CONFIRM_POINT)
        buy_confirm_samples = {
            f"{point[0]},{point[1]}": _pixel(purchase_path, point)
            for point in BUY_CONFIRM_SAMPLE_POINTS
        }
        if not any(_is_blue_buy(rgb) for rgb in buy_confirm_samples.values()):
            raise RuntimeError(
                f"{slot_name}: expected blue purchase button after tapping buy-now, got center={buy_confirm_rgb} samples={buy_confirm_samples}"
            )

        bought_path = self._tap_and_capture(
            BUY_CONFIRM_POINT,
            f"{slot_name}-after-buy-confirm",
            notes="confirm zeny purchase",
            delay_sec=2.8,
        )
        self._record(
            "buy_confirm",
            BUY_CONFIRM_POINT,
            bought_path,
            notes=f"buy_confirm_rgb={buy_confirm_rgb} buy_confirm_samples={buy_confirm_samples}",
        )

        submitted_path = self._tap_and_capture(
            POPUP_SUBMIT_POINT,
            f"{slot_name}-after-popup-submit",
            notes="submit after purchase",
            delay_sec=2.8,
        )
        self._record(
            "submit_popup",
            POPUP_SUBMIT_POINT,
            submitted_path,
            notes=f"buy_now_rgb={buy_now_rgb}",
        )
        return True

    def _process_custom_order(self) -> bool:
        slot_name, point = CUSTOM_ORDER_SLOT
        selected_path = self._tap_and_capture(
            point,
            f"{slot_name}-selected",
            notes="select custom-order card by text/hold region",
        )
        if not self._detect_custom_list_button(selected_path):
            self._record(
                "skip_custom_order",
                point,
                selected_path,
                notes="custom-order list button not visible; likely already submitted or unavailable",
            )
            return False

        list_path = self._tap_and_wait_for_checkpoint(
            CUSTOM_LIST_BUTTON_POINT,
            f"{slot_name}-after-custom-list",
            notes="open custom-order list",
            predicate=self._is_custom_list_panel,
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected custom-order list panel after tapping list button, "
                    f"got submit_rgb={_pixel(screenshot_path, CUSTOM_LIST_PANEL_SUBMIT_POINT)}"
                )
            ),
        )

        quantity_path = self._tap_and_wait_for_checkpoint(
            self._custom_order_point,
            f"{slot_name}-after-backpack-item",
            notes=(
                "open quantity popup for visible row-major backpack item "
                f"index={self._custom_order_index}"
            ),
            predicate=self._is_custom_quantity_popup,
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected quantity popup after tapping visible row-major backpack item "
                    f"index={self._custom_order_index}, "
                    f"got confirm_rgb={_pixel(screenshot_path, CUSTOM_QUANTITY_CONFIRM_POINT)}"
                )
            ),
        )

        ready_path = self._tap_and_wait_for_checkpoint(
            CUSTOM_QUANTITY_CONFIRM_POINT,
            f"{slot_name}-after-quantity-confirm",
            notes="confirm prefilled custom-order quantity",
            predicate=self._is_custom_list_ready_to_submit,
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected custom-order list to become ready after confirming quantity, "
                    f"got submit_rgb={_pixel(screenshot_path, CUSTOM_LIST_PANEL_SUBMIT_POINT)}"
                )
            ),
        )

        submitted_path = self._tap_and_wait_for_checkpoint(
            CUSTOM_LIST_PANEL_SUBMIT_POINT,
            f"{slot_name}-after-custom-submit",
            notes="submit custom-order bonus",
            predicate=self._detect_custom_order_submitted,
            timeout_message=(
                lambda screenshot_path: (
                    f"{slot_name}: expected custom-order card to show submitted overlay after submitting bonus, "
                    f"samples={self._sample_pixels(screenshot_path, CUSTOM_ORDER_SUBMITTED_SAMPLES)}"
                )
            ),
        )

        self._record(
            "submit_custom_order",
            CUSTOM_LIST_PANEL_SUBMIT_POINT,
            submitted_path,
            notes="custom-order bonus submitted and card shows submitted overlay",
        )
        return True

    def _detect_get_button(self, screenshot_path: Path) -> tuple[int, int] | None:
        for candidate in GET_BUTTON_CANDIDATES:
            if any(_is_light_button(_pixel(screenshot_path, point)) for point in candidate["samples"]):
                return tuple(candidate["tap"])
        return None

    def _has_blue_buy_button(self, screenshot_path: Path) -> bool:
        return any(
            _is_blue_buy(rgb)
            for rgb in self._sample_pixels(screenshot_path, BUY_CONFIRM_SAMPLE_POINTS).values()
        )

    def _detect_custom_list_button(self, screenshot_path: Path) -> bool:
        return any(
            _is_custom_list_button(_pixel(screenshot_path, point))
            for point in CUSTOM_LIST_BUTTON_SAMPLES
        )

    def _is_custom_list_panel(self, screenshot_path: Path) -> bool:
        samples = self._sample_pixels(screenshot_path, CUSTOM_LIST_PANEL_SAMPLES)
        return _is_light_button(samples["318,134"]) and _is_orange_button(samples["319,627"])

    def _is_custom_quantity_popup(self, screenshot_path: Path) -> bool:
        return any(
            _is_orange_button(rgb)
            for rgb in self._sample_pixels(screenshot_path, CUSTOM_QUANTITY_CONFIRM_SAMPLES).values()
        )

    def _is_custom_list_ready_to_submit(self, screenshot_path: Path) -> bool:
        return _is_orange_button(_pixel(screenshot_path, CUSTOM_LIST_PANEL_SUBMIT_POINT))

    def _detect_custom_order_submitted(self, screenshot_path: Path) -> bool:
        return any(
            _is_submitted_overlay(rgb)
            for rgb in self._sample_pixels(screenshot_path, CUSTOM_ORDER_SUBMITTED_SAMPLES).values()
        )

    def _tap_and_capture(
        self,
        point: tuple[int, int],
        label: str,
        *,
        notes: str,
        delay_sec: float | None = None,
    ) -> Path:
        self._step_index += 1
        self._adapter.tap(self._instance, point)
        time.sleep(self._tap_delay_sec if delay_sec is None else delay_sec)
        screenshot_path = self._capture(label)
        self._record("tap", point, screenshot_path, notes=notes)
        return screenshot_path

    def _tap_and_wait_for_checkpoint(
        self,
        point: tuple[int, int],
        label: str,
        *,
        notes: str,
        predicate: Callable[[Path], bool],
        timeout_message: Callable[[Path], str],
        initial_delay_sec: float | None = None,
        timeout_sec: float | None = None,
    ) -> Path:
        self._step_index += 1
        self._adapter.tap(self._instance, point)
        poll_result = _poll_for_checkpoint(
            capture=lambda: self._capture(label),
            predicate=predicate,
            initial_delay_sec=self._tap_delay_sec if initial_delay_sec is None else initial_delay_sec,
            poll_interval_sec=self._poll_interval_sec,
            timeout_sec=self._checkpoint_timeout_sec if timeout_sec is None else timeout_sec,
        )
        record_notes = (
            f"{notes} checkpoint_attempts={poll_result.attempt_count} "
            f"elapsed_sec={poll_result.elapsed_sec:.2f}"
        )
        if poll_result.matched:
            self._record("tap", point, poll_result.screenshot_path, notes=record_notes)
            return poll_result.screenshot_path
        self._record("tap_failed_checkpoint", point, poll_result.screenshot_path, notes=record_notes)
        raise RuntimeError(timeout_message(poll_result.screenshot_path))

    def _capture(self, label: str) -> Path:
        path = self._adapter.capture_screenshot(self._instance)
        target = self._output_dir / f"{self._step_index:03d}-{label}.png"
        path.replace(target)
        return target

    def _record(
        self,
        action: str,
        point: tuple[int, int] | None,
        screenshot_path: Path,
        *,
        notes: str = "",
    ) -> None:
        self._records.append(
            ActionRecord(
                step_index=self._step_index,
                action=action,
                point=point,
                screenshot_path=str(screenshot_path),
                notes=notes,
            )
        )
        self._write_report()

    def _write_report(self) -> None:
        report_path = self._output_dir / "actions.json"
        payload = {
            "adb_serial": self._instance.adb_serial,
            "output_dir": str(self._output_dir),
            "custom_order_index": self._custom_order_index,
            "custom_order_backpack_points": [
                {"index": index + 1, "point": point}
                for index, point in enumerate(CUSTOM_BACKPACK_ITEM_POINTS)
            ],
            "slot_points": [{"slot": slot_name, "point": point} for slot_name, point in SLOT_POINTS],
            "records": [asdict(record) for record in self._records],
        }
        report_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _sample_pixels(
        self,
        screenshot_path: Path,
        sample_points: tuple[tuple[int, int], ...],
    ) -> dict[str, tuple[int, int, int]]:
        return {
            f"{point[0]},{point[1]}": _pixel(screenshot_path, point)
            for point in sample_points
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a bounded guild-order current-panel automation probe.")
    parser.add_argument("--serial", required=True, help="ADB serial, for example 127.0.0.1:16480")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "runtime_logs" / "guild-order-runner",
        help="Directory for screenshots and action logs",
    )
    parser.add_argument(
        "--tap-delay-sec",
        type=float,
        default=1.6,
        help="Initial delay after each tap before the first checkpoint capture",
    )
    parser.add_argument(
        "--poll-interval-sec",
        type=float,
        default=0.5,
        help="Polling interval while waiting for a checkpoint to appear",
    )
    parser.add_argument(
        "--checkpoint-timeout-sec",
        type=float,
        default=6.0,
        help="Bounded timeout for one checkpoint transition",
    )
    parser.add_argument(
        "--max-material-actions",
        type=int,
        default=12,
        help="Safety cap for successful material submissions in one run",
    )
    parser.add_argument(
        "--custom-order-index",
        type=int,
        default=1,
        help=(
            "1-based visible backpack item index for self-select order, "
            "counted left-to-right then top-to-bottom. Default: 1"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runner = GuildOrderCurrentPanelRunner(
        serial=args.serial,
        output_root=args.output_root,
        tap_delay_sec=float(args.tap_delay_sec),
        poll_interval_sec=float(args.poll_interval_sec),
        checkpoint_timeout_sec=float(args.checkpoint_timeout_sec),
        max_material_actions=int(args.max_material_actions),
        custom_order_index=int(args.custom_order_index),
    )
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
