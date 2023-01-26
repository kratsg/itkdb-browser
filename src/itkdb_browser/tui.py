from __future__ import annotations

from operator import itemgetter
from typing import Any

import itkdb
from rich.console import RenderableType
from rich.pretty import Pretty
from rich.progress import BarColumn, Progress
from rich.text import Text
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

from itkdb_browser.draggable_list_view import DraggableListItem, DraggableListView


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


class Projects(Horizontal):
    """Display a bunch of buttons for projects."""

    project = reactive("P", layout=True)

    def compose(self) -> ComposeResult:
        for project in self.app.projects:
            is_current_project = project["code"] == self.project
            yield Button(
                project["name"],
                variant="primary" if is_current_project else "default",
                id=project["code"],
                disabled=is_current_project or True,
            )


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
                        screen.name.replace("_", " ").title(),
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


class ListItemByName(ListItem):
    """An ListItem using provided dictionary 'name' key as the display, storing value on itself."""

    def __init__(self, item: dict[str, Any]):
        super().__init__(Label(item["name"]))
        self.value = item


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
                self.append(ListItemByName(institution))
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


class ComponentTypeList(ListView):
    """A widget to display a list of component types."""

    project = reactive("P", layout=True)
    _component_types: dict[str, list[dict[str, Any]]] = {}

    def get_component_types(self) -> list[dict[str, Any]]:
        """Get the list of component types."""
        if not self._component_types.get(self.project):
            self._component_types[self.project] = sorted(
                list(
                    self.app.client.get(
                        "listComponentTypes", json=dict(project=self.project)
                    )
                ),
                key=itemgetter("name"),
            )
        return self._component_types[self.project]

    def watch_project(self, old_project: str, new_project: str) -> None:
        """Update list of component types to correspond with the project."""
        if old_project != new_project:
            self.clear()
            self.on_mount()

    def on_mount(self) -> None:
        for component_type in self.get_component_types():
            self.append(ListItemByName(component_type))


class StagesListView(DraggableListView):
    """A widget to display stages for a component type."""

    component_type: reactive[dict[str, Any]] = reactive({})

    def build_list(self) -> None:
        """Build the list of stages from component type details."""
        self.clear()
        for stage in sorted(
            self.component_type.get("stages", []) or [], key=itemgetter("order")
        ):
            item = DraggableListItem(stage["name"])
            item.value = stage
            self.append(item)

    def watch_component_type(self) -> None:
        """Called when the component_type attribute changes."""
        self.build_list()


class StageReorderScreen(Screen):
    """Screen for reordering stages on a component type."""

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """When component_type has been chosen."""
        if message.sender.id == "component_type_list":
            self.query_one("StagesListView").component_type = getattr(
                message.item, "value", {}
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when  button is pressed."""
        button_id = event.button.id
        stages_lv = self.query_one("StagesListView")
        textlog = self.query_one("TextLog")
        textlog.clear()
        if button_id == "reset":
            stages_lv.build_list()
        elif button_id == "save":
            component_type = stages_lv.component_type
            new_stages = []
            for new_order, child in enumerate(stages_lv.children, start=1):
                stage = child.value
                if stage["order"] != new_order:
                    try:
                        self.app.client.post(
                            "updateComponentTypeStage",
                            json=dict(
                                id=component_type["id"],
                                code=stage["code"],
                                name=stage["name"],
                                order=stage["order"],
                            ),
                        )
                        textlog.write(
                            Text.from_markup(
                                f":white_check_mark: {stage['name']}: {stage['order']} :arrow_forward: {new_order}"
                            )
                        )
                        stage["order"] = new_order
                    except itkdb.exceptions.ResponseException as exc:
                        self.app.bell()
                        textlog.write(
                            Text.from_markup(
                                f":cross_mark: {stage['name']}: {stage['order']} :arrow_forward: {new_order}"
                            )
                        )
                        textlog.write(Text.from_markup(f"[red]{exc}[/red]"))
                new_stages.append(stage)

            # update stages
            component_type["stages"] = new_stages

        event.stop()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Navigation()
        yield Footer()
        ctype_list = ComponentTypeList(id="component_type_list")
        ctype_list.project = self.app.user.get("preferences", {}).get(
            "defaultProject", "P"
        )
        yield Horizontal(
            Vertical(Projects(), ctype_list, classes="column"),
            Vertical(
                Static(
                    Text.from_markup(
                        "Drag and drop stages to reorder. :pinching_hand: (:down_arrow:,:up_arrow: ) :hand:"
                    ),
                    classes="title",
                ),
                StagesListView(),
                Horizontal(
                    Button("Save", variant="success", id="save"),
                    Button("Reset", variant="error", id="reset"),
                ),
                TextLog(),
                id="stages",
                classes="column",
            ),
        )


class Browser(App[Any]):
    """A basic implementation of the itkdb-browser TUI"""

    BINDINGS = [("q", "exit", "Quit"), ("d", "toggle_dark", "Toggle dark mode")]

    # If no name, screen hidden from navigation
    # Order of screens listed is order displayed in navigation
    SCREENS = {
        "login": LoginScreen(),
        "main": MainScreen(name="main"),
        "list_institutions": InstitutionScreen(name="list_institutions"),
        "reorder_stages": StageReorderScreen(name="reorder_stages"),
    }

    CSS_PATH = "tui.css"

    def __init__(self) -> None:
        super().__init__()
        self.dark = True
        self.client = None
        self.user: dict[str, Any] = {}
        self.projects: list[dict[str, Any]] = []

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
        self.projects = list(self.client.get("listProjects"))
        self.pop_screen()
        self.push_screen("main")

    def on_mount(self) -> None:
        """Call after entering application mode."""
        self.push_screen("login")

    def compose(self) -> ComposeResult:
        """Call to compose the app"""
        yield Header()
        yield Footer()
