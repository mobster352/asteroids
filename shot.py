import pygame
from circleshape import CircleShape
from constants import *

class Shot(CircleShape):
    def __init__(self, x, y, radius, id, used):
        super().__init__(x, y, radius)
        self.id = id,
        self.used = used

    def draw(self, screen):
        return pygame.draw.circle(screen, "white", self.position, self.radius, width=2)

    def update(self, dt, screen_width, screen_height):
        self.position += (self.velocity * dt)

    def kill_shot(self, shots):
        shots.remove(self)