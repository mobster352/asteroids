import pygame
from circleshape import CircleShape
import random
from constants import *

from asteroid import Asteroid

class Asteroid_Peer(Asteroid):
    def __init__(self, position, radius):
        super().__init__(position.x, position.y, radius)

    def draw(self, screen):
        pass

    def update(self, dt, screen_width, screen_height):
        pass

    def draw_peer(self, screen):
        return pygame.draw.circle(screen, "white", self.position, self.radius, width=2)