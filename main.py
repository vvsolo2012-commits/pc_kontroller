import json
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


class TouchPadWidget(Widget):
    def __init__(self, send_move_callback, **kwargs):
        super().__init__(**kwargs)
        self.send_move_callback = send_move_callback
        self.last_pos = None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self.last_pos = touch.pos
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos) or self.last_pos is None:
            return super().on_touch_move(touch)
        dx = int(touch.pos[0] - self.last_pos[0])
        dy = int(touch.pos[1] - self.last_pos[1])
        self.last_pos = touch.pos
        if dx != 0 or dy != 0:
            self.send_move_callback(dx, -dy)
        return True

    def on_touch_up(self, touch):
        self.last_pos = None
        return super().on_touch_up(touch)


class ControlTabs(TabbedPanel):
    def __init__(self, send_callback, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.send_callback = send_callback
        self._build_tabs()

    def _build_tabs(self):
        shutdown_tab = TabbedPanelItem(text="Выключение ПК")
        shutdown_tab.content = self._build_shutdown_tab()

        volume_tab = TabbedPanelItem(text="Громкость")
        volume_tab.content = self._build_volume_tab()

        touchpad_tab = TabbedPanelItem(text="Тачпад")
        touchpad_tab.content = self._build_touchpad_tab()

        self.add_widget(shutdown_tab)
        self.add_widget(volume_tab)
        self.add_widget(touchpad_tab)

    def _build_shutdown_tab(self):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        row.add_widget(
            Button(
                text="Выключить через 10 сек",
                on_press=lambda *_: self.send_callback("/shutdown", {"delay": 10}),
            )
        )
        row.add_widget(
            Button(
                text="Отмена выключения",
                on_press=lambda *_: self.send_callback("/cancel_shutdown", {}),
            )
        )
        layout.add_widget(row)
        return layout

    def _build_volume_tab(self):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        row.add_widget(Button(text="Громче", on_press=lambda *_: self._volume("up")))
        row.add_widget(Button(text="Тише", on_press=lambda *_: self._volume("down")))
        row.add_widget(Button(text="Mute", on_press=lambda *_: self._volume("mute")))
        layout.add_widget(row)
        return layout

    def _build_touchpad_tab(self):
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        touchpad = TouchPadWidget(send_move_callback=self._touch_move)
        touchpad.size_hint_y = 1
        layout.add_widget(touchpad)

        click_row = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8))
        click_row.add_widget(Button(text="ЛКМ", on_press=lambda *_: self._click("left", False)))
        click_row.add_widget(Button(text="Двойной клик", on_press=lambda *_: self._click("left", True)))
        click_row.add_widget(Button(text="ПКМ", on_press=lambda *_: self._click("right", False)))
        layout.add_widget(click_row)
        return layout

    def _volume(self, command):
        self.send_callback("/volume", {"command": command, "steps": 2})

    def _touch_move(self, dx, dy):
        self.send_callback("/touchpad/move", {"dx": dx, "dy": dy, "sensitivity": 1.2})

    def _click(self, button, double):
        self.send_callback("/touchpad/click", {"button": button, "double": double})


class PhoneRemoteApp(App):
    status_text = StringProperty("Готово")

    def build(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))

        self.server_url_input = TextInput(
            text="http://192.168.0.10:8765",
            multiline=False,
            hint_text="Адрес ПК сервера",
            size_hint_y=None,
            height=dp(40),
        )
        self.token_input = TextInput(
            text="change_me_12345",
            multiline=False,
            password=True,
            hint_text="Токен",
            size_hint_y=None,
            height=dp(40),
        )
        self.status_label = Label(text=self.status_text, size_hint_y=None, height=dp(30))
        self.bind(status_text=lambda *_: setattr(self.status_label, "text", self.status_text))

        root.add_widget(self.server_url_input)
        root.add_widget(self.token_input)
        root.add_widget(self.status_label)

        tabs = ControlTabs(send_callback=self._post)
        root.add_widget(tabs)
        Clock.schedule_once(lambda *_: setattr(self, "status_text", "Подключите URL и токен"), 0.3)
        return root

    def _headers(self):
        token = self.token_input.text.strip() if self.token_input else ""
        return {"Content-Type": "application/json", "X-Auth-Token": token}

    def _base_url(self):
        return self.server_url_input.text.strip().rstrip("/") if self.server_url_input else ""

    def _post(self, endpoint, payload):
        url = f"{self._base_url()}{endpoint}"
        UrlRequest(
            url,
            req_body=json.dumps(payload),
            req_headers=self._headers(),
            on_success=partial(self._on_success, endpoint),
            on_failure=partial(self._on_failure, endpoint),
            on_error=partial(self._on_error, endpoint),
            timeout=4,
            method="POST",
        )

    def _on_success(self, endpoint, request, result):
        message = result.get("message", "OK") if isinstance(result, dict) else "OK"
        self.status_text = f"{endpoint}: {message}"

    def _on_failure(self, endpoint, request, result):
        self.status_text = f"{endpoint}: ошибка {request.resp_status}"

    def _on_error(self, endpoint, request, error):
        self.status_text = f"{endpoint}: {error}"


if __name__ == "__main__":
    PhoneRemoteApp().run()
