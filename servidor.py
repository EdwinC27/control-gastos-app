"""
servidor.py

Run the app the way a background service would: no reloader, no
console window and everything written to a log file.

This is what the scheduled task launches when you log in. For day to
day development keep using `python app.py`, which does reload on every
change.
"""

import logging
import socket
import sys
from logging.handlers import RotatingFileHandler

import uvicorn

from common import DATA_DIR


HOST = "127.0.0.1"
PORT = 2004

LOG_FILE = DATA_DIR / "servidor.log"


def setup_logging():
    """Everything goes to data/servidor.log (1 MB, 3 files kept)."""

    LOG_FILE.parent.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8"
    )

    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def already_running(host, port):
    """True when something is already listening on that port."""

    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) == 0


def main():

    setup_logging()

    log = logging.getLogger("control-gastos")

    if already_running(HOST, PORT):
        log.warning(
            "Ya hay algo escuchando en %s:%s. No se arranca otra vez.",
            HOST,
            PORT
        )
        return 0

    log.info("Arrancando Control de Gastos en http://%s:%s", HOST, PORT)

    try:
        uvicorn.run(
            "app:app",
            host=HOST,
            port=PORT,
            reload=False,
            log_config=None,
            access_log=False
        )
    except BaseException:
        log.exception("El servidor se detuvo por un error")
        return 1

    log.info("El servidor se detuvo.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
