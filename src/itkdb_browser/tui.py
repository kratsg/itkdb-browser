from __future__ import annotations

from operator import itemgetter
from typing import Any

import itkdb
from rich.pretty import Pretty
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static


class InstitutionItem(ListItem):
    """An Institution ListItem."""

    __slots__ = ("value",)

    def __init__(self, institution: dict[str, Any]):
        super().__init__(Label(institution["name"]))
        self.value = institution


class InstitutionList(ListView):
    """A widget to display a list of institutions."""

    institutions: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, client: itkdb.Client, classes: str = ""):
        self.client = client
        super().__init__(classes=classes)

    def load_institutions(self) -> None:
        """Retrieve institutions from API."""
        self.institutions = list(self.client.get("listInstitutions"))

    def on_mount(self) -> None:
        """Call after mounting."""
        self.load_institutions()

    def watch_institutions(self) -> None:
        """Called when the institutions attribute changes."""
        self.clear()
        for institution in sorted(self.institutions, key=itemgetter("name")):
            self.append(InstitutionItem(institution))


class InstitutionDisplay(Static):
    """A widget to display institution details."""

    institution: reactive[dict[str, Any]] = reactive({})

    def watch_institution(self) -> None:
        """Called when the institution attribute changes."""
        self.update(Pretty(self.institution))


class Browser(App[Any]):
    """A basic implementation of the itkdb-browser TUI"""

    BINDINGS = [("q", "exit", "Quit"), ("d", "toggle_dark", "Toggle dark mode")]

    DEFAULT_CSS = """
    Browser > Static {
        content-align: center middle;
        background: crimson;
        border: solid darkred;
        height: 1fr;
    }

    .column {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.institution_list = InstitutionList(itkdb.Client(), classes="column")
        self.institution_details = InstitutionDisplay()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit(self) -> None:
        """An action to exit."""
        self.exit()

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """When institution has been chosen."""
        self.institution_details.institution = getattr(message.item, "value", {})

    def compose(self) -> ComposeResult:
        """Call to compose the app"""
        yield Header()
        yield Footer()
        yield Horizontal(
            self.institution_list, Vertical(self.institution_details, classes="column")
        )
        self.set_focus(self.institution_list)
