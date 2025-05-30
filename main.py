# this allows us to use code from
# the open-source pygame library
# throughout this file
import pygame
import pygame.freetype

from constants import *
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from ui import UI
import os
import pickle

def process_keys(event_list, player):
    for event in event_list:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                player.pause = not player.pause

def main():
    print("Starting Asteroids!")
    print(f"Screen width: {SCREEN_WIDTH}")
    print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")
    # pygame.display.toggle_fullscreen()
    clock = pygame.time.Clock()
    dt = 0
    fps = 60
    font = pygame.freetype.Font("./fonts/Rogbold-3llGM.otf", 30)

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    ui_drawable = pygame.sprite.Group()

    Player.containers = (updatable, drawable)
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    Asteroid.containers = (asteroids, updatable, drawable)

    AsteroidField.containers = (updatable,)
    AsteroidField()

    Shot.containers = (shots, updatable, drawable)

    ui = UI(0, 0)

    # Load data
    filename = "./data/data.pickle"
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, "rb") as f:
            loaded_data = pickle.load(f)
            ui.update_high_score(loaded_data["high_score"])

    while True:
        event_list = pygame.event.get()

        for event in event_list:
            if event.type == pygame.QUIT:
                return

        process_keys(event_list, player)
        
        screen.fill("black")

        # ======== UI START =========== #

        score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
        screen.blit(score_surface, (20, 10))

        score_surface, rect = font.render(f"High Score: {ui.get_high_score()}", "white", (0,0,0))
        screen.blit(score_surface, (200, 10))

        # ======== UI END =========== #

        if player.pause:
            player.update(dt)
        else:
            updatable.update(dt)
            for d in drawable:
                d.draw(screen)

            for a in asteroids:
                if a.check_collisions(player):
                    print("Game Over!")
                    
                    # Save data
                    if ui.get_high_score() < ui.get_score():
                        ui.update_high_score(ui.get_score())
                        with open(filename, "wb") as f:
                            data = {"high_score": ui.get_high_score()}
                            pickle.dump(data, f)
                    return
                for s in shots:
                    if a.check_collisions(s):
                        a.split()
                        s.kill()
                        ui.update_score(10)
            pygame.display.flip()
            
        dt = clock.tick(fps) / 1000

if __name__ == "__main__":
    main()