"""Keyboard and mouse to actions and camera moves."""

import pygame

from game.content import display as D

# Actions that fire once per key press (the rest are held).
_TRIGGERS = ("toggle_view", "toggle_glow", "toggle_stats", "new_site", "quit",
             "pause", "speed_up", "speed_down", "sell", "centre",
             "build", "research", "orbit", "contracts", "production", "minimap", "clock", "priority", "cancel_site", "icons", "sound")


class Input:
    def __init__(self):
        self.keys = {action: tuple(pygame.key.key_code(name) for name in names)
                     for action, names in D.KEY_BINDINGS.items()}
        self.dragging = False
        self.drag_px = 0
        self.mouse = (0, 0)
        self.mouse_inside = False
        self.click = None  # screen position of a left click (press and release without dragging)
        self.right_click = None
        self.typed = []    # characters typed this frame (upper case), for menus
        self.keys_down = []  # pygame key codes pressed this frame
        self.mouse_moved = False
        self.panning_enabled = True

    def process(self, events, camera):
        """Handle this frame's events. Returns the triggered actions."""
        actions = []
        self.click = None
        self.right_click = None
        self.typed = []
        self.keys_down = []
        self.mouse_moved = False
        for event in events:
            if event.type == pygame.QUIT:
                actions.append("quit")
            elif event.type == pygame.KEYDOWN:
                self.keys_down.append(event.key)
                if event.unicode and event.unicode.isalnum():
                    self.typed.append(event.unicode.upper())
                for action in _TRIGGERS:
                    if event.key in self.keys[action]:
                        shifted = action == "sell" and event.mod & pygame.KMOD_SHIFT
                        actions.append("sell_all" if shifted else action)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
                self.mouse_moved = True
                self.mouse_inside = True
                if self.dragging:
                    self.drag_px += abs(event.rel[0]) + abs(event.rel[1])
                    # Small wobbles during a click don't pan.
                    if camera is not None and self.drag_px > D.CLICK_MAX_DRAG_PX:
                        camera.pan_pixels(*event.rel)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self.right_click = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in D.PAN_DRAG_BUTTONS:
                self.dragging = True
                self.drag_px = 0
            elif event.type == pygame.MOUSEBUTTONUP and event.button in D.PAN_DRAG_BUTTONS:
                if event.button == 1 and self.drag_px <= D.CLICK_MAX_DRAG_PX:
                    self.click = event.pos
                self.dragging = False
            elif event.type == pygame.MOUSEWHEEL and camera is not None and event.y:
                camera.zoom_at(D.ZOOM_WHEEL_FACTOR ** event.y, *self.mouse)
            elif event.type == pygame.WINDOWLEAVE:
                self.mouse_inside = False
        return actions

    def apply_held(self, camera, dt):
        if not self.panning_enabled:
            return
        pressed = pygame.key.get_pressed()

        def held(action):
            return any(pressed[k] for k in self.keys[action])

        step = D.PAN_KEY_SPEED_PX_PER_S * dt
        dx = (held("pan_left") - held("pan_right")) * step
        dy = (held("pan_up") - held("pan_down")) * step
        if dx or dy:
            camera.pan_pixels(dx, dy)
        zoom = held("zoom_in") - held("zoom_out")
        if zoom:
            camera.zoom_at(D.ZOOM_KEY_FACTOR_PER_S ** (zoom * dt), camera.sw / 2, camera.sh / 2)
