import pygame
from constants import *
from circleshape import CircleShape
from shot import Shot

class Player(CircleShape):
    def __init__(self, x:int, y:int, color:str):
        super().__init__(x, y, PLAYER_RADIUS)
        self.color = color
        self.rotation = 0
        self.timer = 0
        self.pause = False
        self.shots = []
        self.shot_timer = 0
        self.shot_id = 0

    # in the player class
    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        return pygame.draw.polygon(screen, self.color, self.triangle(), width=2)

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt, screen_width, screen_height):
        keys = pygame.key.get_pressed()

        if self.timer > 0:
            self.timer -= dt
        if self.shot_timer > 0:
            self.shot_timer -= dt
        # elif self.shot_timer <= 0 and len(self.shots) > 0:
        #     # print("remove")
        #     self.shots.pop(0)

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

        if ENABLE_SOUNDS:
            # pygame.mixer.Sound(ENGINE_SOUND_FILE).play()
            pass

    def shoot(self):
        shot = Shot(self.position.x, self.position.y, SHOT_RADIUS, self.shot_id)
        shot.velocity = pygame.Vector2(0, 1).rotate(self.rotation) * PLAYER_SHOOT_SPEED
        self.shot_id += 1
        self.shots.append(shot)
        self.timer = PLAYER_SHOOT_COOLDOWN
        self.shot_timer = 0.15
        if ENABLE_SOUNDS:
            pygame.mixer.Sound(LASER_SOUND_FILE).play()

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

    def get_position(self):
        return self.position

    def get_rotation(self):
        return self.rotation

    def get_shots(self):
        return [s for s in self.shots if s.alive()]