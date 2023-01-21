from __future__ import annotations

from operator import itemgetter
from typing import Any

import itkdb
from rich.pretty import Pretty
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextLog,
)


class LoginScreen(Screen):
    """Screen for logging user in."""

    access_code1 = reactive(itkdb.settings.ITKDB_ACCESS_CODE1)
    access_code2 = reactive(itkdb.settings.ITKDB_ACCESS_CODE2)

    def login(self) -> None:
        """Called to perform login."""
        try:
            user = itkdb.core.User(
                accessCode1=self.access_code1, accessCode2=self.access_code2
            )
            user.authenticate()
            self.app.client = itkdb.Client(user=user)  # type: ignore[attr-defined]
            self.app.login()  # type: ignore[attr-defined]
        except itkdb.exceptions.ResponseException as exc:
            self.app.bell()
            self.query_one("TextLog").write(str(exc))  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when login button is pressed."""
        button_id = event.button.id
        if button_id == "login":
            self.login()
            event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        """When someone types in the input."""
        if event.input.id == "accessCode1":
            self.access_code1 = event.value
            event.stop()
        elif event.input.id == "accessCode2":
            self.access_code2 = event.value
            event.stop()
        else:
            pass

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Container(
            Horizontal(
                Static("Access Code 1", classes="labels"),
                Input(
                    self.access_code1,
                    placeholder="code",
                    id="access_code1",
                    classes="access_codes",
                ),
                classes="input_row",
            ),
            Horizontal(
                Static("Access Code 2", classes="labels"),
                Input(
                    self.access_code2,
                    placeholder="code",
                    id="access_code2",
                    classes="access_codes",
                ),
                classes="input_row",
            ),
            Button("Login", id="login", variant="primary"),
            id="dialog",
        )
        yield Horizontal(TextLog(), id="textlog")


class InstitutionItem(ListItem):
    """An Institution ListItem."""

    __slots__ = ("value",)

    def __init__(self, institution: dict[str, Any]):
        super().__init__(Label(institution["name"]))
        self.value = institution


class InstitutionList(ListView):
    """A widget to display a list of institutions."""

    def load_institutions(self) -> None:
        """Load up the institutions in the list view."""
        self.clear()
        institutions = self.app.client.get("listInstitutions")  # type: ignore[attr-defined]
        for institution in sorted(
            list(institutions),
            key=itemgetter("name"),
        ):
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

    SCREENS = {"login": LoginScreen()}

    CSS_PATH = "tui.css"

    def __init__(self) -> None:
        super().__init__()
        self.institution_list = InstitutionList(classes="column")
        self.institution_details = InstitutionDisplay()
        self.client = None

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit(self) -> None:
        """An action to exit."""
        self.exit()

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """When institution has been chosen."""
        self.institution_details.institution = getattr(message.item, "value", {})

    def login(self) -> None:
        """Called when the LoginScreen has logged in."""
        self.pop_screen()
        self.institution_list.load_institutions()

    def on_mount(self) -> None:
        """Call after entering application mode."""
        self.push_screen("login")

    def compose(self) -> ComposeResult:
        """Call to compose the app"""
        yield Header()
        yield Footer()
        yield Horizontal(
            self.institution_list, Vertical(self.institution_details, classes="column")
        )
