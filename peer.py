import pygame
from constants import *
from circleshape import CircleShape
from shot import Shot

from player import Player

class Peer(Player):
    def __init__(self, x, y, color):
        super().__init__(x, y, color)

    def update_position(self, position):
        if position is not None:
            self.position = pygame.Vector2(position[0], position[1])

    def update_rotation(self, rotation):
        self.rotation = rotation

    def update(self, dt, screen_width, screen_height):
        pass

    def draw(self, screen):
        pass

    def draw_peer(self, screen):
        return pygame.draw.polygon(screen, self.color, self.triangle(), width=2)