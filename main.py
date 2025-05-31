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
from button import Button

def process_keys(event_list, player):
    for event in event_list:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and player is not None:
                player.pause = not player.pause

def setup_game(updatable, drawable, asteroids, shots, screen_width, screen_height, filename):
    Player.containers = (updatable, drawable)
    player = Player(screen_width / 2, screen_height / 2)

    Asteroid.containers = (asteroids, updatable, drawable)

    AsteroidField.containers = (updatable,)
    AsteroidField(screen_width, screen_height)

    Shot.containers = (shots, updatable, drawable)

    ui = UI(0, 0)

    # Load data
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, "rb") as f:
            loaded_data = pickle.load(f)
            ui.update_high_score(loaded_data["high_score"])

    return player, ui

def main():
    print("Starting Asteroids!")
    # print(f"Screen width: {SCREEN_WIDTH}")
    # print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")
    # pygame.display.toggle_fullscreen()
    clock = pygame.time.Clock()
    dt = 0
    fps = 60
    font = pygame.freetype.Font(os.path.abspath("fonts/Rogbold-3llGM.otf"), 30)
    menu_font = pygame.freetype.Font(os.path.abspath("fonts/Rogbold-3llGM.otf"), 80)

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

    player = None

    run = True

    in_menu = True

    new_game_button = Button("New Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    quit_game_button = Button("Quit Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    filename = os.path.abspath("data/data.pickle")

    while run:
        window_size = pygame.display.get_window_size()
        dynamic_screen_width = window_size[0]
        dynamic_screen_height = window_size[1]

        event_list = pygame.event.get()

        for event in event_list:
            if event.type == pygame.QUIT:
                run = False

        process_keys(event_list, player)

        if in_menu:

            for event in event_list:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if new_game_button.check_collisions(mouse_pos):
                        player, ui = setup_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename)
                        in_menu = False
                    if quit_game_button.check_collisions(mouse_pos):
                        run = False

            # ========== Main Menu Start ============ #

            screen.fill("black")

            menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
            # rect - (x, y, w, h)

            rect_width_center = rect[2] / 2
            rect_height_center = rect[3] / 2

            screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

            new_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
            new_game_button.draw_button("white", "blue", font, screen)

            quit_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
            quit_game_button.draw_button("white", "red", font, screen)

            pygame.display.flip()
            dt = clock.tick(fps) / 1000
            # ========== Main Menu End ========== #

        else:

            # ========== Game Start ========= #
            
            screen.fill("black")

            # ======== UI START =========== #

            score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
            screen.blit(score_surface, (20, 10))

            score_surface, rect = font.render(f"High Score: {ui.get_high_score()}", "white", (0,0,0))
            screen.blit(score_surface, (200, 10))

            # ======== UI END =========== #

            if player.pause:
                pass
            else:
                updatable.update(dt, dynamic_screen_width, dynamic_screen_height)
                for d in drawable:
                    d.draw(screen)

                for a in asteroids:
                    if a.check_collisions(player):
                        print("Game Over!")
                        asteroids.empty()
                        shots.empty()
                        updatable.empty()
                        drawable.empty()
                        
                        # Save data
                        if ui.get_high_score() < ui.get_score():
                            ui.update_high_score(ui.get_score())
                            with open(filename, "wb") as f:
                                data = {"high_score": ui.get_high_score()}
                                pickle.dump(data, f)
                        in_menu = True
                    for s in shots:
                        if a.check_collisions(s):
                            a.split()
                            s.kill()
                            ui.update_score(10)
                pygame.display.flip()

            dt = clock.tick(fps) / 1000

            # ============= Game End ============ #

if __name__ == "__main__":
    main()