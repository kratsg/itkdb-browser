from __future__ import annotations

from operator import itemgetter
from typing import Any

import itkdb
from rich.console import RenderableType
from rich.pretty import Pretty
from rich.progress import BarColumn, Progress
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.timer import Timer
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


class IntervalUpdater(Static):
    """Interval updater for rendering animating renderables."""

    _renderable_object: RenderableType

    def __init__(self, renderable_object: RenderableType) -> None:
        super().__init__(renderable_object)
        self.interval_update: Timer | None = None

    def on_mount(self) -> None:
        """Start updating the interval once the widget is mounted."""
        self.interval_update = self.set_interval(1 / 60, self.refresh)


class IndeterminateProgressBar(IntervalUpdater):
    """Basic indeterminate progress bar widget based on rich.progress.Progress."""

    def __init__(self) -> None:
        self._renderable_object = Progress(BarColumn(bar_width=None))
        self._renderable_object.add_task("", total=None)
        super().__init__(self._renderable_object)


class LoginScreen(Screen):
    """Screen for logging user in."""

    access_code1 = itkdb.settings.ITKDB_ACCESS_CODE1
    access_code2 = itkdb.settings.ITKDB_ACCESS_CODE2

    def login(self) -> None:
        """Called to perform login."""
        try:
            user = itkdb.core.User(
                accessCode1=self.access_code1, accessCode2=self.access_code2
            )
            user.authenticate()
            self.app.client = itkdb.Client(user=user)
            self.app.login()
        except itkdb.exceptions.ResponseException as exc:
            self.app.bell()
            self.query_one("TextLog").write(str(exc))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when login button is pressed."""
        button_id = event.button.id
        if button_id == "login":
            self.login()
            event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        """When someone types in the input."""
        if event.input.id == "access_code1":
            self.access_code1 = event.value
            event.stop()
        elif event.input.id == "access_code2":
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


class UserDetails(Static):
    """Widget for displaying user information."""

    def on_mount(self) -> None:
        """Generate static block of text for user details when mounted."""
        email = self.app.user["email"]
        text = f"""[b]{self.app.user['firstName']} {self.app.user['lastName']}[/b] [link=mailto:{email} lightblue]({email})[/link]
[b]Identity:[/b] {self.app.client.user.identity}"""
        preferences = self.app.user.get("preferences", {})
        if preferences:
            text += """\n[u yellow]Preferences:[/u yellow]"""
            for pref, value in preferences.items():
                text += f"\n  {pref}: {value}"
        self.update(text)


class UserInstitutionDetails(Static):
    """Widget for displaying institution information."""

    def __init__(self, institution: dict[str, Any], **kwargs: Any):
        super().__init__("institution details", **kwargs)
        self._id = institution["id"]
        self._code = institution["code"]
        self._name = institution["name"]
        self._roles = {}
        for role in [
            "default",
            "executive",
            "authority",
            "componentManager",
            "clusterManager",
        ]:
            self._roles[role] = bool(institution.get(role))
        self._notifications = {}
        for notification in ["shipping", "tests", "components"]:
            self._notifications[notification] = bool(
                (institution.get("notification") or {}).get(notification)
            )

    def _render_bool_str(self, value: bool) -> str:
        return ":white_check_mark:" if value else ":cross_mark:"

    def on_mount(self) -> None:
        """Generate static block of text for user institution details when mounted."""
        text = f"[b]{self._name} [gray]({self._code})[/gray][/b]"
        text += "\n[u yellow]Roles:[/u yellow]"
        for role, value in self._roles.items():
            text += f"\n  {self._render_bool_str(value)} {role}"
        text += "\n[u yellow]Notification:[/u yellow]"
        for notify, value in self._notifications.items():
            text += f"\n  {self._render_bool_str(value)} {notify}"
        self.update(text)


class Navigation(Horizontal):
    """Display a bunch of buttons for app navigation."""

    def __init__(self, classes: str | None = None):
        children = []
        current_screen = self.app.screen
        for screen in self.app._installed_screens.values():
            is_current_screen = screen == current_screen
            if isinstance(screen, Screen) and screen.name:
                children.append(
                    Button(
                        screen.name.title(),
                        variant="primary" if is_current_screen else "default",
                        id=screen.name,
                        disabled=is_current_screen,
                    )
                )
        super().__init__(*children, classes=classes)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """When a button is clicked, switch screen based on the screen.name stored in the button id."""
        if event.button.id:
            self.app.switch_screen(event.button.id)


class MainScreen(Screen):
    """Screen for displaying user information."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Navigation()
        yield Footer()
        yield UserDetails()
        for institution in self.app.user["institutions"]:
            yield UserInstitutionDetails(institution)


class InstitutionItem(ListItem):
    """An Institution ListItem."""

    __slots__ = ("value",)

    def __init__(self, institution: dict[str, Any]):
        super().__init__(Label(institution["name"]))
        self.value = institution


class InstitutionList(ListView):
    """A widget to display a list of institutions."""

    _loaded = False

    def on_mount(self) -> None:
        """Load up the institutions in the list view."""
        if not self._loaded:
            self.clear()
            institutions = self.app.client.get("listInstitutions")
            for institution in sorted(
                list(institutions),
                key=itemgetter("name"),
            ):
                self.append(InstitutionItem(institution))
        self._loaded = True


class InstitutionDisplay(Static):
    """A widget to display institution details."""

    institution: reactive[dict[str, Any]] = reactive({})

    def watch_institution(self) -> None:
        """Called when the institution attribute changes."""
        self.update(Pretty(self.institution))


class InstitutionScreen(Screen):
    """Screen for displaying institutions."""

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """When institution has been chosen."""
        self.query_one("InstitutionDisplay").institution = getattr(
            message.item, "value", {}
        )

    def compose(self) -> ComposeResult:
        yield Header()
        yield Navigation()
        yield Footer()
        yield Horizontal(
            InstitutionList(classes="column"),
            Vertical(InstitutionDisplay(), classes="column"),
        )


class Browser(App[Any]):
    """A basic implementation of the itkdb-browser TUI"""

    BINDINGS = [("q", "exit", "Quit"), ("d", "toggle_dark", "Toggle dark mode")]

    # If no name, screen hidden from navigation
    # Order of screens listed is order displayed in navigation
    SCREENS = {
        "login": LoginScreen(),
        "main": MainScreen(name="main"),
        "institution": InstitutionScreen(name="institution"),
    }

    CSS_PATH = "tui.css"

    def __init__(self) -> None:
        super().__init__()
        self.dark = True
        self.client = None
        self.user = None

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_exit(self) -> None:
        """An action to exit."""
        self.exit()

    def login(self) -> None:
        """Called when the LoginScreen has logged in."""
        self.user = self.client.get(
            "getUser", json=dict(userIdentity=self.client.user.identity)
        )
        self.pop_screen()
        self.push_screen("main")

    def on_mount(self) -> None:
        """Call after entering application mode."""
        self.push_screen("login")

    def compose(self) -> ComposeResult:
        """Call to compose the app"""
        yield Header()
        yield Footer()
