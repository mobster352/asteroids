import pygame
from constants import *
from circleshape import CircleShape
from shot import Shot

class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.timer = 0
        self.pause = False

    # in the player class
    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        return pygame.draw.polygon(screen, "white", self.triangle(), width=2)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt, screen_width, screen_height):
        keys = pygame.key.get_pressed()

        if self.timer > 0:
            self.timer -= dt

        if keys[pygame.K_a]:
            self.rotate(-dt)
        if keys[pygame.K_d]:
            self.rotate(dt)
        if keys[pygame.K_w]:
            self.move(dt, screen_width, screen_height)
        if keys[pygame.K_s]:
            self.move(-dt, screen_width, screen_height)
        if keys[pygame.K_SPACE] and self.timer <= 0:
            self.shoot()

    def move(self, dt, screen_width, screen_height):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        self.position += forward * PLAYER_SPEED * dt

        self.__check_off_screen(screen_width, screen_height)

    def shoot(self):
        shot = Shot(self.position.x, self.position.y, SHOT_RADIUS)
        shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation) * PLAYER_SHOOT_SPEED
        self.timer = PLAYER_SHOOT_COOLDOWN

    def __check_off_screen(self, screen_width, screen_height):
        units_off_screen = 10
        if self.position[0] >= screen_width + units_off_screen:
            self.position[0] = -units_off_screen
        elif self.position[0] <= -units_off_screen:
            self.position[0] = screen_width
        elif self.position[1] <= -units_off_screen:
            self.position[1] = screen_height
        elif self.position[1] >= screen_height + units_off_screen:
            self.position[1] = -units_off_screen