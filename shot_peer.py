import pygame
from circleshape import CircleShape
from constants import *
from shot import Shot

class Shot_Peer(Shot):
    def __init__(self, x, y, radius, id, used):
        super().__init__(x, y, radius, id, used)

    def draw(self, screen):
        pass

    def update(self, dt, screen_width, screen_height):
        pass

    def draw_peer(self, screen):
        return pygame.draw.circle(screen, "white", self.position, self.radius, width=2)