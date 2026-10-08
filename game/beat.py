import pygame
import random

LANES = 4
LANE_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
LANE_LABELS = ['D', 'F', 'J', 'K']
LANE_COLORS = [(220,80,80),(80,180,220),(100,220,100),(220,180,60)]


class Note:
    WIDTH = 70
    HEIGHT = 20
    HOLD_DURATION_MS = 1000

    def __init__(self, lane, y=-30, speed=4, is_hold=False):
        self.lane = lane
        self.y = y
        self.speed = speed
        self.is_hold = is_hold
        self.hit = False
        self.missed = False
        self.holding = False
        self.hold_started_at = None

        # Make the visible hold body approximately one second of travel.
        self.hold_length = max(
            self.HEIGHT,
            int(self.speed * 60 * self.HOLD_DURATION_MS / 1000),
        ) if self.is_hold else self.HEIGHT

    def update(self):
        self.y += self.speed

    def get_rect(self, lane_x):
        return pygame.Rect(
            lane_x - self.WIDTH // 2,
            int(self.y),
            self.WIDTH,
            self.hold_length,
        )
