"""Keep one test browser open and run Python snippets in it.

    tools/live.py serve         start the browser and wait for snippets
    tools/live.py run < x.py    run a snippet; `driver` and the helpers from
                                spotify_session are in scope and persist
    echo quit | tools/live.py run    close the browser
"""
import contextlib
import io
import os
import socket
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
SOCKET = ROOT / ".cache" / "live.sock"
CONNECT_TIMEOUT_S = 60


def serve():
    from browser import start_firefox
    import spotify_session

    driver = start_firefox(headless=False)
    driver.set_window_size(1400, 900)
    driver.get("https://open.spotify.com")
    scope = {"driver": driver, **vars(spotify_session)}

    SOCKET.unlink(missing_ok=True)
    os.umask(0o177)  # only this user may send code to the browser
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(SOCKET))
    server.listen()
    try:
        while True:
            conn, _ = server.accept()
            with conn:
                code = conn.makefile("rb").read().decode()
                if code.strip() == "quit":
                    return
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    try:
                        exec(code, scope)
                    except Exception:
                        traceback.print_exc(file=output)
                conn.sendall(output.getvalue().encode())
    finally:
        driver.quit()
        SOCKET.unlink(missing_ok=True)


def run():
    code = sys.stdin.read().encode()
    deadline = time.time() + CONNECT_TIMEOUT_S
    while True:
        client = socket.socket(socket.AF_UNIX)
        try:
            client.connect(str(SOCKET))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            client.close()
            if time.time() > deadline:
                sys.exit("live browser is not running")
            time.sleep(0.5)
    with client:
        client.sendall(code)
        client.shutdown(socket.SHUT_WR)
        print(client.makefile("rb").read().decode(), end="")


if __name__ == "__main__":
    {"serve": serve, "run": run}[sys.argv[1]]()
