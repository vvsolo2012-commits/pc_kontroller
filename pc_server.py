import argparse
import ctypes
import json
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

DEFAULT_TOKEN = "change_me_12345"


def press_virtual_key(vk_code: int) -> None:
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


def change_volume(command: str, steps: int = 1) -> None:
    key_map = {
        "up": VK_VOLUME_UP,
        "down": VK_VOLUME_DOWN,
        "mute": VK_VOLUME_MUTE,
    }
    vk_code = key_map.get(command)
    if vk_code is None:
        raise ValueError("Unknown volume command")

    if command == "mute":
        press_virtual_key(vk_code)
        return

    for _ in range(max(1, steps)):
        press_virtual_key(vk_code)


def move_mouse(dx: int, dy: int, sensitivity: float = 1.0) -> None:
    move_x = int(dx * sensitivity)
    move_y = int(dy * sensitivity)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)


def mouse_click(button: str, double: bool = False) -> None:
    button_map = {
        "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    }
    events = button_map.get(button)
    if events is None:
        raise ValueError("Unknown button")

    down_event, up_event = events
    count = 2 if double else 1
    for _ in range(count):
        ctypes.windll.user32.mouse_event(down_event, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up_event, 0, 0, 0, 0)


class PCControlHandler(BaseHTTPRequestHandler):
    server_version = "PCControl/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_json(self) -> dict:
        content_len = int(self.headers.get("Content-Length", "0"))
        if content_len <= 0:
            return {}
        raw_body = self.rfile.read(content_len).decode("utf-8")
        if not raw_body.strip():
            return {}
        return json.loads(raw_body)

    def _is_authorized(self) -> bool:
        token = self.headers.get("X-Auth-Token", "")
        return token == self.server.auth_token

    def do_GET(self) -> None:
        if self.path == "/ping":
            self._send_json(HTTPStatus.OK, {"ok": True, "service": "pc-control"})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        if not self._is_authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
            return

        try:
            data = self._parse_json()
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid JSON"})
            return

        try:
            if self.path == "/shutdown":
                self._handle_shutdown(data)
            elif self.path == "/cancel_shutdown":
                self._handle_cancel_shutdown()
            elif self.path == "/volume":
                self._handle_volume(data)
            elif self.path == "/touchpad/move":
                self._handle_touchpad_move(data)
            elif self.path == "/touchpad/click":
                self._handle_touchpad_click(data)
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def _handle_shutdown(self, data: dict) -> None:
        delay = int(data.get("delay", 10))
        if delay < 0:
            raise ValueError("delay must be >= 0")
        subprocess.run(["shutdown", "/s", "/t", str(delay)], check=True)
        self._send_json(HTTPStatus.OK, {"ok": True, "message": f"Shutdown in {delay}s"})

    def _handle_cancel_shutdown(self) -> None:
        subprocess.run(["shutdown", "/a"], check=True)
        self._send_json(HTTPStatus.OK, {"ok": True, "message": "Shutdown cancelled"})

    def _handle_volume(self, data: dict) -> None:
        command = str(data.get("command", "")).lower()
        steps = int(data.get("steps", 1))
        change_volume(command, steps=steps)
        self._send_json(HTTPStatus.OK, {"ok": True, "message": f"Volume {command}"})

    def _handle_touchpad_move(self, data: dict) -> None:
        dx = int(data.get("dx", 0))
        dy = int(data.get("dy", 0))
        sensitivity = float(data.get("sensitivity", 1.0))
        move_mouse(dx, dy, sensitivity=sensitivity)
        self._send_json(HTTPStatus.OK, {"ok": True})

    def _handle_touchpad_click(self, data: dict) -> None:
        button = str(data.get("button", "left")).lower()
        double = bool(data.get("double", False))
        mouse_click(button=button, double=double)
        self._send_json(HTTPStatus.OK, {"ok": True, "message": f"{button} click"})

    def log_message(self, format: str, *args) -> None:
        # Keep output clean in console while still allowing manual prints if needed.
        return


class PCControlServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_cls, auth_token: str):
        super().__init__(server_address, handler_cls)
        self.auth_token = auth_token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PC control HTTP server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Auth token shared with phone app")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = PCControlServer((args.host, args.port), PCControlHandler, auth_token=args.token)
    print(f"PC control server listening on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
