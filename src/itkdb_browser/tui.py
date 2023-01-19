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


class Browser(App[Any]):
    """A basic implementation of the itkdb-browser TUI"""

    DEFAULT_CSS = """
        Browser {
            width: 100%;
            height: 100%;
            background: $surface;
        }
        Browser Container {
            padding: 1;
            background: $panel;
            color: $text;
        }
        Browser #text {
            margin:  0 1;
        }
        Browser #close {
            dock: bottom;
            width: 100%;
        }
    """

    def on_mount(self) -> None:
        """Call after terminal goes in to application mode"""
        self.screen.styles.background = "darkblue"
        self.screen.styles.border = ("heavy", "white")

    def on_button_pressed(self) -> None:
        """Call when a button is pressed"""
        self.exit()

    def compose(self) -> ComposeResult:
        """Call to compose the app"""
        yield Container(Static(Markdown(WELCOME_MD), id="text"), id="md")
        yield Button("OK", id="close", variant="success")
