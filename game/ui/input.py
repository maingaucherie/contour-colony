"""Keyboard and mouse to actions and camera moves."""

import pygame

from game.content import display as D

# Actions that fire once per key press (the rest are held).
_TRIGGERS = ("toggle_view", "toggle_glow", "toggle_stats", "new_site", "quit")


class Input:
    def __init__(self):
        self.keys = {action: tuple(pygame.key.key_code(name) for name in names)
                     for action, names in D.KEY_BINDINGS.items()}
        self.dragging = False
        self.mouse = (0, 0)
        self.mouse_inside = False

    def process(self, events, camera):
        """Handle this frame's events. Returns the triggered actions."""
        actions = []
        for event in events:
            if event.type == pygame.QUIT:
                actions.append("quit")
            elif event.type == pygame.KEYDOWN:
                for action in _TRIGGERS:
                    if event.key in self.keys[action]:
                        actions.append(action)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
                self.mouse_inside = True
                if self.dragging and camera is not None:
                    camera.pan_pixels(*event.rel)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in D.PAN_DRAG_BUTTONS:
                self.dragging = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button in D.PAN_DRAG_BUTTONS:
                self.dragging = False
            elif event.type == pygame.MOUSEWHEEL and camera is not None and event.y:
                camera.zoom_at(D.ZOOM_WHEEL_FACTOR ** event.y, *self.mouse)
            elif event.type == pygame.WINDOWLEAVE:
                self.mouse_inside = False
        return actions

    def apply_held(self, camera, dt):
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
