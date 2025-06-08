import pygame
from circleshape import CircleShape
import random
from constants import *

class Asteroid(CircleShape):
    def __init__(self, x, y, radius, id):
        super().__init__(x, y, radius)
        self.id = id

    # @classmethod
    # def new_asteroid(cls, position:pygame.Vector2, radius:int):
    #     return cls(position.x, position.y, radius)

    def draw(self, screen):
        return pygame.draw.circle(screen, "white", self.position, self.radius, width=2)

    def update(self, dt, screen_width, screen_height):
        self.position += (self.velocity * dt)
        self.__check_off_screen(screen_width, screen_height)

    def split(self, asteroid_field):
        # print("hit")
        asteroid_field.asteroids.remove(self)
        if self.radius <= ASTEROID_MIN_RADIUS:
            if ENABLE_SOUNDS:
                pygame.mixer.Sound(EXPLOSION_L_SOUND_FILE).play()
            self.kill()
            return asteroid_field.asteroids
        angle = random.uniform(20, 50)

        vector1 = self.velocity.rotate(angle)
        vector2 = self.velocity.rotate(-angle)

        new_radius = self.radius - ASTEROID_MIN_RADIUS

        new_asteroid_1 = Asteroid(self.position.x, self.position.y, new_radius, asteroid_field.get_next_id())
        new_asteroid_2 = Asteroid(self.position.x, self.position.y, new_radius, asteroid_field.get_next_id())

        new_asteroid_1.velocity = vector1 * 1.2
        new_asteroid_2.velocity = vector2 * 1.2

        asteroid_field.asteroids.append(new_asteroid_1)
        asteroid_field.asteroids.append(new_asteroid_2)

        if ENABLE_SOUNDS:
            pygame.mixer.Sound(EXPLOSION_L_SOUND_FILE).play()

        self.kill()
        return asteroid_field.asteroids

    def __check_off_screen(self, screen_width, screen_height):
        units_off_screen = 100
        if self.position[0] >= screen_width + units_off_screen:
            self.position[0] = -units_off_screen
        elif self.position[0] <= -units_off_screen:
            self.position[0] = screen_width
        elif self.position[1] <= -units_off_screen:
            self.position[1] = screen_height
        elif self.position[1] >= screen_height + units_off_screen:
            self.position[1] = -units_off_screen
