from __future__ import annotations

from typing import Any

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static

WELCOME_MD = """\
# Welcome!

This is the itkdb-browser.
"""


class MainApp(App[Any]):
    DEFAULT_CSS = """
        MainApp {
            width: 100%;
            height: 100%;
            background: $surface;
        }
        MainApp Container {
            padding: 1;
            background: $panel;
            color: $text;
        }
        MainApp #text {
            margin:  0 1;
        }
        MainApp #close {
            dock: bottom;
            width: 100%;
        }
    """

    def on_mount(self) -> None:
        self.screen.styles.background = "darkblue"
        self.screen.styles.border = ("heavy", "white")

    def on_button_pressed(self) -> None:
        self.exit()

    def compose(self) -> ComposeResult:
        yield Container(Static(Markdown(WELCOME_MD), id="text"), id="md")
        yield Button("OK", id="close", variant="success")
