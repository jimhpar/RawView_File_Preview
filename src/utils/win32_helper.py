import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QGuiApplication

user32 = ctypes.windll.user32

def calculate_popup_position(cursor_x: int, cursor_y: int, popup_w: int, popup_h: int) -> QPoint:
    """
    Calculates the optimal screen position for the floating preview HUD.
    Ensures the HUD stays within the monitor boundaries and does not overlap the cursor.
    """
    screen = QGuiApplication.screenAt(QPoint(cursor_x, cursor_y))
    if not screen:
        screen = QGuiApplication.primaryScreen()

    if not screen:
        return QPoint(cursor_x + 20, cursor_y + 20)

    avail = screen.availableGeometry()
    screen_left = avail.left()
    screen_top = avail.top()
    screen_right = avail.right()
    screen_bottom = avail.bottom()

    offset_x = 24
    offset_y = 24

    # Default to bottom-right of cursor
    target_x = cursor_x + offset_x
    target_y = cursor_y + offset_y

    # If overflowing right edge, position to the left of the cursor
    if target_x + popup_w > screen_right:
        target_x = cursor_x - popup_w - offset_x

    # If still overflowing left edge, clamp to left margin
    if target_x < screen_left + 10:
        target_x = screen_left + 10

    # If overflowing bottom edge, position above the cursor
    if target_y + popup_h > screen_bottom:
        target_y = cursor_y - popup_h - offset_y

    # If still overflowing top edge, clamp to top margin
    if target_y < screen_top + 10:
        target_y = screen_top + 10

    return QPoint(int(target_x), int(target_y))
