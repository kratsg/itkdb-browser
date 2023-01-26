from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual import events
from textual._types import MessageTarget
from textual.message import Message
from textual.widgets import Label, ListItem, ListView


class DraggableListItem(ListItem, can_focus=False):
    """
    A draggable list item.
    """

    mouse_down = False
    is_dragging = False
    x = 0
    y = 0

    class DragMessage(Message):
        """Sent for any drag-related events."""

        def __init__(self, sender: MessageTarget, mouse_event: events.MouseEvent):
            self.mouse_event = mouse_event
            super().__init__(sender)

    class DragStart(DragMessage):
        """Sent when the mouse starts dragging."""

    class DragMove(DragMessage):
        """Sent when the mouse is dragging."""

    class DragStop(DragMessage):
        """Sent when the mouse stops dragging."""

    def __init__(self, label: str):
        super().__init__(Label(f"[orange]{label}[/orange]"))
        self.value = label

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """When a mouse left-button is pressed."""
        if event.button != 1:
            return
        self.mouse_down = True
        self.capture_mouse(capture=True)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """When a mouse left-button is released."""
        if event.button != 1:
            return
        self.mouse_down = False
        if self.is_dragging:
            self.emit_no_wait(self.DragStop(self, event))
            self.is_dragging = False
        self.capture_mouse(capture=False)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """When the mouse moves."""
        if self.mouse_down and (event.delta_x != 0 or event.delta_y != 0):
            if not self.is_dragging:
                self.emit_no_wait(self.DragStart(self, event))
                self.is_dragging = True
            else:
                self.emit_no_wait(self.DragMove(self, event))


class DraggableListView(ListView):
    """Displays a sortable ListView."""

    DEFAULT_CSS = """

    DraggableListView {
        border: round blue;
        height: 100%;
        background: $panel;
        content-align: center middle;
        padding: 0 3;
    }
    """

    def on_draggable_list_item_drag_start(
        self, message: DraggableListItem.DragStart
    ) -> None:
        """When a user starts dragging a list item."""
        self.index = self.children.index(message.sender)

    def on_draggable_list_item_drag_move(
        self, message: DraggableListItem.DragMove
    ) -> None:
        """While a user is dragging a list item."""
        index_sender = self.children.index(message.sender)
        new_index = self._clamp_index(index_sender + message.mouse_event.y)

        self.children._remove(message.sender)  # type: ignore[arg-type] # pylint: disable=protected-access
        self.children._insert(new_index, message.sender)  # type: ignore[arg-type] # pylint: disable=protected-access
        self.index = new_index

        # Request a refresh.
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        if len(self.children):
            return super().render()
        return Text.from_markup(":exclamation_mark: Nothing to see here")
