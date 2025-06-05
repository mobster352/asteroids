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

import threading
from client import Client
from peer import Peer

def process_keys(event_list, player):
    for event in event_list:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and player is not None:
                player.pause = not player.pause

def setup_game(updatable, drawable, asteroids, shots, screen_width, screen_height, filename):
    Player.containers = (updatable, drawable)
    player = Player(screen_width / 2, screen_height / 2)
    peer = Peer(screen_width / 2, screen_height / 2)

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

    return player, ui, peer

def main():
    bg = pygame.image.load(BACKGROUND_IMAGE)
    #os.environ['SDL_AUDIODRIVER'] = 'dsp'

    print("Starting Asteroids!")
    # print(f"Screen width: {SCREEN_WIDTH}")
    # print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()
    
    if ENABLE_SOUNDS:
        pygame.mixer.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Asteroids")
    # pygame.display.toggle_fullscreen()
    clock = pygame.time.Clock()
    dt = 0
    fps = 60

    host, port = '127.0.0.1', 65432

    font = pygame.freetype.Font(os.path.realpath(FONT_FILE), 30)
    menu_font = pygame.freetype.Font(os.path.realpath(FONT_FILE), 80)
    filename = os.path.abspath(SAVE_FILE)

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

    player = None
    peer = None

    run = True

    in_menu = True

    new_game_button = Button("New Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    client_connect_button = Button("Join Server", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    quit_game_button = Button("Quit Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 3)

    is_multiplayer_game = False

    if ENABLE_SOUNDS:
        print(f"Mixer init: {pygame.mixer.get_init()}")

    while run:
        window_size = pygame.display.get_window_size()
        dynamic_screen_width = window_size[0]
        dynamic_screen_height = window_size[1]

        bg = pygame.transform.smoothscale(bg, (dynamic_screen_width, dynamic_screen_height))

        event_list = pygame.event.get()

        for event in event_list:
            if event.type == pygame.QUIT:
                if ENABLE_SOUNDS:
                    pygame.mixer.quit()
                run = False

        process_keys(event_list, player)

        if in_menu:

            for event in event_list:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if new_game_button.check_collisions(mouse_pos):
                        player, ui = setup_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename)
                        in_menu = False
                    elif quit_game_button.check_collisions(mouse_pos):
                        run = False
                    elif client_connect_button.check_collisions(mouse_pos):
                        client = Client(host, port)
                        client_thread = threading.Thread(target=client.connect)
                        client_thread.daemon = True
                        client_thread.start()
                        player, ui, peer = setup_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename)
                        in_menu = False
                        is_multiplayer_game = True

            # ========== Main Menu Start ============ #

            screen.fill("black")
            screen.blit(bg, (0,0))

            menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
            # rect - (x, y, w, h)

            rect_width_center = rect[2] / 2
            rect_height_center = rect[3] / 2

            screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

            new_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
            new_game_button.draw_button("white", "blue", font, screen)

            client_connect_button.update_button(dynamic_screen_width, dynamic_screen_height)
            client_connect_button.draw_button("white", "blue", font, screen)

            quit_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
            quit_game_button.draw_button("white", "red", font, screen)

            pygame.display.flip()
            dt = clock.tick(fps) / 1000
            # ========== Main Menu End ========== #

        elif is_multiplayer_game:

            # ========== Multiplayer Game Start ========== #

            screen.fill("black")
            screen.blit(bg, (0,0))

            # ======== UI START =========== #

            score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
            screen.blit(score_surface, (20, 10))

            # score_surface, rect = font.render(f"High Score: {ui.get_high_score()}", "white", (0,0,0))
            # screen.blit(score_surface, (200, 10))

            # ======== UI END =========== #

            updatable.update(dt, dynamic_screen_width, dynamic_screen_height)
            for d in drawable:
                d.draw(screen)

            for a in asteroids:
                if a.check_collisions(player):
                    if ENABLE_SOUNDS:
                        pygame.mixer.Sound(SHIP_EXPLOSION).play()
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
                    client.kill_client()
                for s in shots:
                    if a.check_collisions(s):
                        a.split()
                        s.kill()
                        ui.update_score(10)

            # update client
            client.update_position(player.get_position())
            client.update_rotation(player.get_rotation())

            # update peer
            if client.peer_data is not None:
                peer.update_position(client.peer_data["position"])
                peer.update_rotation(client.peer_data["rotation"])
                peer.draw(screen)

            pygame.display.flip()

            dt = clock.tick(fps) / 1000

            # ========== Multiplayer Game End ========== #

        else:

            # ========== Game Start ========= #
            
            screen.fill("black")
            screen.blit(bg, (0,0))

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
                        if ENABLE_SOUNDS:
                            pygame.mixer.Sound(SHIP_EXPLOSION).play()
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