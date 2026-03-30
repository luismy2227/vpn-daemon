from __future__ import annotations

import logging
import queue
import threading
import time

from vpn_daemon.config import load_config, default_state_dir
from vpn_daemon.network import NetworkChangePoller
from vpn_daemon.openvpn import OpenVpnRunner, VpnLinkState
from vpn_daemon.schedule import should_auto_reconnect, within_work_hours
from vpn_daemon.state import StateStore
from vpn_daemon.tray_app import TrayController, UiState

log = logging.getLogger(__name__)

LINK_POLL_SECONDS = 2.0
LOOP_SLEEP = 0.25


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    store = StateStore(default_state_dir() / "state.json")
    rt = store.load()
    ui = UiState(paused=rt.daemon_paused, user_disconnected=rt.user_disconnected)

    ctrl: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    tray = TrayController(ctrl, ui)
    runner_ref: list[OpenVpnRunner | None] = [None]

    def persist() -> None:
        store.save(ui.snapshot_persist())

    def daemon_loop() -> None:
        runner = OpenVpnRunner(config)
        runner_ref[0] = runner

        last_net_poll = 0.0
        last_link_poll = 0.0
        last_vpn_policy_check = 0.0
        backoff_seconds = 0.0
        next_retry_at = 0.0
        last_openvpn_start_at = 0.0

        def mark_openvpn_started() -> None:
            nonlocal last_openvpn_start_at
            last_openvpn_start_at = time.monotonic()

        def on_network_change() -> None:
            ctrl.put("network_flap")

        poller = NetworkChangePoller(
            config.network_poll_interval_seconds,
            config.network_reconnect_debounce_seconds,
            on_network_change,
        )

        def handle_msg(msg: str) -> None:
            nonlocal backoff_seconds, next_retry_at
            if msg == "quit":
                log.info("Quit requested")
                runner.stop()
                stop_event.set()
                tray.stop()
                return
            if msg == "toggle_pause":
                ui.toggle_pause()
                log.info("Daemon paused=%s", ui.is_paused())
                persist()
                return
            if msg == "disconnect":
                ui.set_user_disconnected(True)
                runner.stop()
                backoff_seconds = 0.0
                next_retry_at = 0.0
                persist()
                log.info("User disconnect; OpenVPN stopped")
                return
            if msg == "reconnect":
                ui.set_user_disconnected(False)
                runner.stop()
                backoff_seconds = 0.0
                next_retry_at = 0.0
                persist()
                time.sleep(1)
                try:
                    runner.start()
                    mark_openvpn_started()
                except OSError as e:
                    log.error("Reconnect start failed: %s", e)
                    backoff_seconds = min(120.0, max(5.0, backoff_seconds * 2 or 5.0))
                    next_retry_at = time.monotonic() + backoff_seconds
                return
            if msg == "network_flap":
                if not should_auto_reconnect(config):
                    return
                if ui.is_paused() or ui.user_wants_disconnected():
                    return
                quiet = time.monotonic() - last_openvpn_start_at
                if quiet < config.network_ignore_seconds_after_vpn_start:
                    log.debug(
                        "Ignoring network flap (%.0fs after last OpenVPN start)",
                        quiet,
                    )
                    return
                log.info("Network change: restarting OpenVPN")
                runner.stop()
                time.sleep(1)
                try:
                    runner.start()
                    mark_openvpn_started()
                except OSError as e:
                    log.error("Network-flap restart failed: %s", e)
                    backoff_seconds = min(120.0, max(5.0, backoff_seconds * 2 or 5.0))
                    next_retry_at = time.monotonic() + backoff_seconds
                return

        while not stop_event.is_set():
            now = time.monotonic()

            try:
                while True:
                    handle_msg(ctrl.get_nowait())
                    if stop_event.is_set():
                        break
            except queue.Empty:
                pass

            if stop_event.is_set():
                break

            in_hours = within_work_hours(config)
            ui.set_flags(within_hours=in_hours)

            if now - last_net_poll >= config.network_poll_interval_seconds:
                poller.tick()
                last_net_poll = now

            if now - last_link_poll >= LINK_POLL_SECONDS:
                link = runner.effective_link_state()
                ui.set_link(link)
                last_link_poll = now
                if link == VpnLinkState.CONNECTED:
                    backoff_seconds = 0.0
                    next_retry_at = 0.0

            if now - last_vpn_policy_check >= config.check_interval_seconds:
                last_vpn_policy_check = now
                eff = runner.effective_link_state()
                ui.set_link(eff)

                auto_ok = (
                    should_auto_reconnect(config)
                    and not ui.is_paused()
                    and not ui.user_wants_disconnected()
                )
                if auto_ok and eff == VpnLinkState.DISCONNECTED and now >= next_retry_at:
                    try:
                        runner.start()
                        mark_openvpn_started()
                        next_retry_at = 0.0
                    except OSError as e:
                        log.error("Auto-start failed: %s", e)
                        backoff_seconds = min(120.0, max(5.0, backoff_seconds * 2 or 5.0))
                        next_retry_at = now + backoff_seconds

            time.sleep(LOOP_SLEEP)

        runner.stop()
        log.info("Daemon loop exit")

    worker = threading.Thread(target=daemon_loop, daemon=True)
    worker.start()
    try:
        tray.run()
    finally:
        stop_event.set()
        r = runner_ref[0]
        if r is not None:
            r.stop()
        worker.join(timeout=20)


if __name__ == "__main__":
    main()
