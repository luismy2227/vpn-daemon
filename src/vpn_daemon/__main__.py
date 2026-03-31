from __future__ import annotations

import logging
import queue
import threading
import time

from vpn_daemon.config import CredentialsMissingError, default_config_path, load_config
from vpn_daemon.openvpn import OpenVpnRunner, VpnLinkState
from vpn_daemon.platforms import get_platform_backend
from vpn_daemon.tray_app import TrayController, icon_for_state

log = logging.getLogger(__name__)


def main() -> None:
    platform_backend = get_platform_backend()
    platform_backend.ensure_elevated_or_relaunch()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config_path = default_config_path()
    try:
        config = load_config(config_path)
    except (FileNotFoundError, CredentialsMissingError) as exc:
        if isinstance(exc, FileNotFoundError):
            log.info("Config not found at %s — launching setup wizard.", config_path)
        else:
            log.info("Credentials missing — launching setup wizard.")
        from vpn_daemon.setup_wizard import CANCELLED, CLEARED, SAVED, run_setup_wizard

        outcome = run_setup_wizard(config_path)
        if outcome != SAVED:
            if outcome == CLEARED:
                log.info("Settings cleared. Exiting.")
            elif outcome == CANCELLED:
                log.info("Setup cancelled. Exiting.")
            else:
                log.info("Setup finished without save. Exiting.")
            return
        config = load_config(config_path)

    ctrl: queue.Queue[str] = queue.Queue()
    stop = threading.Event()
    runner_ref: list[OpenVpnRunner | None] = [None]
    tray = TrayController(config, ctrl)

    def _tray_title(last_verb: str, running: bool) -> str:
        tail = f"Last: {last_verb} · {'running' if running else 'stopped'}"
        base = config.tray_tooltip.strip()
        merged = f"{base} — {tail}" if base else tail
        return merged[:120]

    def worker_loop(icon) -> None:
        runner = OpenVpnRunner(config, platform_backend=platform_backend)
        runner_ref[0] = runner
        last_verb = "idle"
        prev_st = VpnLinkState.DISCONNECTED

        if config.auto_connect:
            try:
                runner.start()
                last_verb = "auto-connect"
            except Exception as e:
                log.error("auto_connect failed: %s", e)
                last_verb = "auto-connect failed"

        while not stop.is_set():
            try:
                msg = ctrl.get(timeout=0.5)
            except queue.Empty:
                msg = None

            if msg == "toggle":
                if runner.is_process_alive():
                    runner.stop()
                    last_verb = "disconnect"
                else:
                    try:
                        runner.start()
                        last_verb = "connect"
                    except Exception as e:
                        log.error("connect failed: %s", e)
                        last_verb = "connect failed"
            elif msg == "connect":
                try:
                    runner.start()
                    last_verb = "connect"
                except Exception as e:
                    log.error("connect failed: %s", e)
                    last_verb = "connect failed"
            elif msg == "disconnect":
                runner.stop()
                last_verb = "disconnect"
            elif msg == "reconnect":
                runner.stop()
                last_verb = "reconnect"
                time.sleep(1.0)
                try:
                    runner.start()
                except Exception as e:
                    log.error("reconnect failed: %s", e)
                    last_verb = "reconnect failed"
            elif msg == "settings":
                def _open_wizard() -> None:
                    from vpn_daemon.setup_wizard import run_setup_wizard
                    run_setup_wizard(config_path)
                threading.Thread(target=_open_wizard, daemon=True).start()
            elif msg == "quit":
                runner.stop()
                stop.set()
                try:
                    icon.stop()
                except Exception as e:
                    log.debug("icon.stop: %s", e)
                break

            if stop.is_set():
                break

            try:
                st = (
                    runner.effective_link_state()
                    if runner.is_process_alive()
                    else VpnLinkState.DISCONNECTED
                )
                if st != prev_st:
                    tray.notify_state_change(prev_st, st)
                    prev_st = st
                icon.icon = icon_for_state(st)
                try:
                    icon.title = _tray_title(last_verb, runner.is_process_alive())
                except Exception as e:
                    log.debug("tray title: %s", e)
            except Exception as e:
                log.debug("tray icon update: %s", e)

        runner.stop()
        runner_ref[0] = None

    try:
        tray.run(after_visible=worker_loop)
    finally:
        stop.set()
        r = runner_ref[0]
        if r is not None:
            r.stop()
        log.info("Exit")


if __name__ == "__main__":
    main()
