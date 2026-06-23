"""Helpers for responsive CTkScrollableFrame scrolling."""
import sys

import customtkinter as ctk

# Pixels moved per standard mouse-wheel notch (delta=±120 on Windows).
DEFAULT_PIXELS_PER_NOTCH = 80


def _wheel_units(event, *, pixels_per_notch: int = DEFAULT_PIXELS_PER_NOTCH) -> int:
    """Signed scroll amount in canvas units (pixels when yscrollincrement=1)."""
    num = getattr(event, "num", None)
    if num == 4:
        return -pixels_per_notch
    if num == 5:
        return pixels_per_notch

    delta = getattr(event, "delta", 0) or 0
    if delta == 0:
        return 0

    if sys.platform.startswith("win"):
        units = int(round(-delta / 120.0 * pixels_per_notch))
    elif sys.platform == "darwin":
        units = int(round(-delta * 2.0))
    else:
        units = int(round(-delta / 120.0 * pixels_per_notch))

    # Touchpads emit small deltas; CTk's int(delta/6) often becomes 0 — always move.
    if units == 0:
        units = -1 if delta > 0 else 1
    return units


def _pointer_inside(widget) -> bool:
    try:
        if not widget.winfo_exists():
            return False
        x = widget.winfo_pointerx() - widget.winfo_rootx()
        y = widget.winfo_pointery() - widget.winfo_rooty()
        return 0 <= x <= widget.winfo_width() and 0 <= y <= widget.winfo_height()
    except Exception:
        return False


def _widget_in_scroll_region(widget, scroll_frame, hover_targets) -> bool:
    if any(_pointer_inside(target) for target in hover_targets):
        return True
    current = widget
    while current is not None:
        if current in hover_targets:
            return True
        if current == scroll_frame or current == scroll_frame._parent_frame:
            return True
        current = getattr(current, "master", None)
    return False


def _enable_scrollbar_drag(scrollbar, canvas):
    """Allow click-and-drag on the CTk scrollbar thumb/track."""
    drag = {"active": False, "start_root_y": 0, "start_top": 0.0}
    sb_canvas = scrollbar._canvas

    def on_press(event):
        drag["active"] = True
        drag["start_root_y"] = event.y_root
        drag["start_top"] = canvas.yview()[0]

    def on_motion(event):
        if not drag["active"]:
            return
        track_h = max(scrollbar.winfo_height(), 1)
        lo, hi = canvas.yview()
        visible = hi - lo
        scrollable = max(1.0 - visible, 0.001)
        thumb_h = max(visible * track_h, scrollbar._minimum_pixel_length)
        movable = max(track_h - thumb_h, 1)
        dy = event.y_root - drag["start_root_y"]
        delta = (dy / movable) * scrollable
        new_top = max(0.0, min(scrollable, drag["start_top"] + delta))
        canvas.yview_moveto(new_top)

    def on_release(_event):
        drag["active"] = False

    sb_canvas.bind("<ButtonPress-1>", on_press, add="+")
    sb_canvas.bind("<B1-Motion>", on_motion, add="+")
    sb_canvas.bind("<ButtonRelease-1>", on_release, add="+")


def setup_smooth_scroll(
    scroll_frame: ctk.CTkScrollableFrame,
    *,
    hover_widgets=(),
    scrollbar_width: int = 22,
    pixels_per_notch: int = DEFAULT_PIXELS_PER_NOTCH,
    page_fraction: float = 0.92,
):
    """Improve wheel scrolling and scrollbar usability for a CTkScrollableFrame."""
    canvas = scroll_frame._parent_canvas
    scrollbar = scroll_frame._scrollbar

    try:
        scrollbar.configure(width=scrollbar_width, height=0)
    except Exception:
        pass

    try:
        scroll_frame.configure(
            scrollbar_fg_color=("#D1D5DB", "#3F3F46"),
            scrollbar_button_color=("#9CA3AF", "#52525B"),
            scrollbar_button_hover_color=("#6B7280", "#71717A"),
        )
    except Exception:
        pass

    _enable_scrollbar_drag(scrollbar, canvas)

    hover_targets = list(hover_widgets) + [scroll_frame._parent_frame, scrollbar]

    def _can_scroll_vertical() -> bool:
        lo, hi = canvas.yview()
        return hi - lo < 0.999

    def _can_scroll_horizontal() -> bool:
        lo, hi = canvas.xview()
        return hi - lo < 0.999

    def scroll_by_units(units: int):
        if units == 0:
            return
        if scroll_frame._orientation == "horizontal":
            if not _can_scroll_horizontal():
                return
            canvas.xview("scroll", units, "units")
            return
        if not _can_scroll_vertical():
            return
        canvas.yview("scroll", units, "units")

    def scroll_by_page(direction: int):
        if scroll_frame._orientation == "horizontal":
            lo, hi = canvas.xview()
        else:
            lo, hi = canvas.yview()
        visible = hi - lo
        scrollable = max(1.0 - visible, 0.001)
        step = direction * page_fraction * scrollable
        new_lo = max(0.0, min(scrollable, lo + step))
        if scroll_frame._orientation == "horizontal":
            canvas.xview_moveto(new_lo)
        else:
            canvas.yview_moveto(new_lo)

    def on_wheel(event):
        if not _widget_in_scroll_region(event.widget, scroll_frame, hover_targets):
            return
        scroll_by_units(_wheel_units(event, pixels_per_notch=pixels_per_notch))
        return "break"

    def on_page_up(event):
        if not _widget_in_scroll_region(event.widget, scroll_frame, hover_targets):
            return
        scroll_by_page(-1)
        return "break"

    def on_page_down(event):
        if not _widget_in_scroll_region(event.widget, scroll_frame, hover_targets):
            return
        scroll_by_page(1)
        return "break"

    for sequence, handler in (
        ("<MouseWheel>", on_wheel),
        ("<Button-4>", on_wheel),
        ("<Button-5>", on_wheel),
        ("<Prior>", on_page_up),
        ("<Next>", on_page_down),
    ):
        scroll_frame.bind_all(sequence, handler, add="+")

    # Disable CTk's default wheel handler (int(delta/6) truncates touchpad input to 0).
    scroll_frame.check_if_master_is_canvas = lambda widget: False
    scroll_frame._bind_scroll_children = lambda: None
    return scroll_frame


def bind_scroll_children(_scroll_frame: ctk.CTkScrollableFrame):
    """Kept for compatibility; hover-based scrolling does not need child rebinding."""
    return
