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
from shot_peer import Shot_Peer
from ui import UI
import os
import pickle
from button import Button

import threading

from server import Server
from client import Client
from peer import Peer

import time

import threading

lock = threading.Lock()

def process_keys(event_list, player):
    for event in event_list:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and player is not None:
                player.pause = not player.pause

def setup_game(updatable, drawable, asteroids, shots, screen_width, screen_height, filename):
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers = (shots, updatable, drawable)

    player = Player(screen_width / 2, screen_height / 2, "white")
    
    asteroid_field = AsteroidField(screen_width, screen_height)

    ui = UI(0, 0)

    # Load data
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, "rb") as f:
            loaded_data = pickle.load(f)
            ui.update_high_score(loaded_data["high_score"])

    return player, ui, asteroid_field

def setup_multiplayer_game(updatable, drawable, asteroids, shots, screen_width, screen_height, filename, client):
    Player.containers = (updatable, drawable)
    Asteroid.containers = (asteroids, updatable, drawable)
    Shot.containers = (shots, updatable, drawable)
    Shot_Peer.containers = (shots, updatable, drawable)

    asteroid_field = None

    with lock:
        if client.num_connections == 2:
            player = Player(screen_width / 2 + 100, screen_height / 2, "cyan")

            AsteroidField.containers = (updatable,)
            asteroid_field = AsteroidField(screen_width, screen_height)
            client.asteroids = asteroid_field.asteroids
            client.id = 2
        else:
            player = Player(screen_width / 2 - 100, screen_height / 2, "cyan")
            client.id = 1

    peer = Peer(screen_width / 2, screen_height / 2, "teal")

    ui = UI(0, 0)

    # Load data
    # if os.path.exists(filename) and os.path.getsize(filename) > 0:
    #     with open(filename, "rb") as f:
    #         loaded_data = pickle.load(f)
    #         ui.update_high_score(loaded_data["high_score"])

    return player, ui, peer, asteroid_field

def main():
    bg = pygame.image.load(BACKGROUND_IMAGE)
    os.environ['SDL_AUDIODRIVER'] = 'dsp'

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
    fps = 120

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
    server = None
    client = None
    server_thread = None
    client_thread = None

    menu = IN_MENU

    new_game_button = Button("New Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    join_room_button = Button("Join Room", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    quit_game_button = Button("Quit Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 1.65)

    multiplayer_button = Button("Multiplayer", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    create_room_button = Button("Create Room", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    main_menu_button = Button("Main Menu", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 1.65)

    if ENABLE_SOUNDS:
        print(f"Mixer init: {pygame.mixer.get_init()}")

    try:
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

            if menu == IN_MENU:

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if new_game_button.check_collisions(mouse_pos):
                            player, ui, asteroid_field = setup_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename)
                            menu = IN_SINGLEPLAYER_GAME
                        elif quit_game_button.check_collisions(mouse_pos):
                            run = False
                        elif multiplayer_button.check_collisions(mouse_pos):
                            menu = IN_MULTIPLAYER_MENU

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

                # join_room_button.update_button(dynamic_screen_width, dynamic_screen_height)
                # join_room_button.draw_button("white", "blue", font, screen)

                multiplayer_button.update_button(dynamic_screen_width, dynamic_screen_height)
                multiplayer_button.draw_button("white", "blue", font, screen)

                quit_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                quit_game_button.draw_button("white", "red", font, screen)

                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ========== Main Menu End ========== #

            elif menu == IN_MULTIPLAYER_MENU:

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if create_room_button.check_collisions(mouse_pos):
                            server = Server(HOST, PORT)
                            server_thread = threading.Thread(target=server.start_server)
                            server_thread.daemon = True
                            server_thread.start()
                            time.sleep(0.01)

                            client = Client(CLIENT_HOST, PORT)
                            client_thread = threading.Thread(target=client.connect, args=(lock,))
                            client_thread.daemon = True
                            client_thread.start()

                            time.sleep(0.01)

                            player, ui, peer, asteroid_field = setup_multiplayer_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename, client)

                            menu = IN_MULTIPLAYER_GAME                                                
                        elif join_room_button.check_collisions(mouse_pos):
                            client = Client(CLIENT_HOST, PORT)
                            client_thread = threading.Thread(target=client.connect, args=(lock,))
                            client_thread.daemon = True
                            client_thread.start()

                            time.sleep(0.01)

                            player, ui, peer, asteroid_field = setup_multiplayer_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename, client)

                            menu = IN_MULTIPLAYER_GAME
                        elif main_menu_button.check_collisions(mouse_pos):
                            menu = IN_MENU

                # ========== Multiplayer Menu Start ============ #

                screen.fill("black")
                screen.blit(bg, (0,0))

                menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
                # rect - (x, y, w, h)

                rect_width_center = rect[2] / 2
                rect_height_center = rect[3] / 2

                screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

                create_room_button.update_button(dynamic_screen_width, dynamic_screen_height)
                create_room_button.draw_button("white", "blue", font, screen)

                join_room_button.update_button(dynamic_screen_width, dynamic_screen_height)
                join_room_button.draw_button("white", "blue", font, screen)

                main_menu_button.update_button(dynamic_screen_width, dynamic_screen_height)
                main_menu_button.draw_button("white", "blue", font, screen)

                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ========== Multiplayer Menu End ========== #


            elif menu == IN_MULTIPLAYER_GAME:

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if quit_game_button.check_collisions(mouse_pos):
                            run = False

                # ========== Multiplayer Game Start ========== #

                screen.fill("black")
                screen.blit(bg, (0,0))

                # ======== UI START =========== #

                score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
                screen.blit(score_surface, (20, 10))

                # score_surface, rect = font.render(f"High Score: {ui.get_high_score()}", "white", (0,0,0))
                # screen.blit(score_surface, (200, 10))

                # ======== UI END =========== #

                # if client.id == 1:
                #     asteroids = client.asteroids

                with lock:
                    if client.id == 1:
                        for s in client.shots:
                            if s.alive():
                                # print(f"kill s: {s.id, s.used}")
                                if s.used:
                                    # print(f"kill s: {s.id}")
                                    s.kill()

                    shots.empty()
                    # shots.add(client.shots)
                    shots.add(*[s for s in client.shots if s.alive()])
                    
                    shots.add(*[s for s in client.peer_shots if s.alive()])
                    # shots.add(client.peer_shots)
                    # for s in shots.sprites():
                    #     # if isinstance(s, Shot_Peer):
                    #     print(f"shots: {s.id}")
                    asteroids.empty()
                    asteroids.add(*[a for a in client.asteroids if a.alive()])

                updatable.update(dt, dynamic_screen_width, dynamic_screen_height)
                for d in drawable:
                    d.draw(screen)

                if client.id == 1:
                    for a in client.asteroids:
                        if not a.alive():
                            continue
                        a.draw_peer(screen)

                if client.peer_shots:
                    for s in client.peer_shots:
                        if not s.alive():
                            continue
                        s.draw_peer(screen)

                # print(f"Shots on screen: {len(shots)}")
                # print(f"Client shots: {len(client.shots)}")
                # print(f"Peer shots: {len(client.peer_shots)}")

                # print(f"Client Asteroids: {len(asteroids)}")
                # print(f"Peer Asteroids: {len(client.asteroids)}")
                            
                with lock:
                    if player.shots:
                        client.shots = player.get_shots()
                    else:
                        for s in client.shots:
                            s.kill()  # remove from sprite groups (shots, drawable, etc.)
                        client.shots = []
                    
                    hit = False
                    for a in client.asteroids:
                        if not a.alive():
                            continue
                        if a.id == client.destroy_asteroid_id and client.id == 2:
                            client.asteroids = a.split(asteroid_field)
                            client.destroy_asteroid_id = None
                            continue
                        if a.check_collisions(player):
                            if ENABLE_SOUNDS:
                                pygame.mixer.Sound(SHIP_EXPLOSION).play()
                            print("Game Over!")
                            asteroids.empty()
                            shots.empty()
                            updatable.empty()
                            drawable.empty()
                            menu = IN_MENU
                            client.kill_client()
                        for s in shots:
                            # print(f"Shot id: {s.id}")
                            if not s.alive():
                                continue
                            if a.check_collisions(s):
                                hit = True
                                if client.id == 2:
                                    client.asteroids = a.split(asteroid_field)
                                    s.used = True                                
                                    if isinstance(s, Shot_Peer):
                                        if client.peer_shots:
                                            if s in client.peer_shots:
                                                client.peer_shots.remove(s)
                                    else:
                                        # print(s.position)
                                        if client.shots:
                                            if s in client.shots:
                                                client.shots.remove(s)
                                        if s in player.shots:
                                            s.kill_shot(player.shots)
                                        ui.update_score(10)
                                    s.kill()
                                    break
                                else:
                                    # client 1 needs to give client 2 the destroyed shot
                                    # then client 1 can kill
                                    # if s.used:
                                    #     s.kill()
                                    client.destroy_asteroid(a.id)
                                    s.kill()
                        if hit:
                            break
                        # print("break")
                            
                    # update client
                    client.update_position(player.get_position())
                    client.update_rotation(player.get_rotation())

                    # update peer
                    if client.peer_data is not None and client.peer_data.get("is_connected"):
                        peer.update_position(client.peer_data.get("position"))
                        peer.update_rotation(client.peer_data.get("rotation"))
                        peer.draw_peer(screen)

                # for s in player.shots:
                #     print(s.position)
                # print("break")

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
                            menu = IN_MENU
                        for s in shots:
                            if a.check_collisions(s):
                                asteroid_field.asteroids = a.split(asteroid_field)
                                s.kill()
                                ui.update_score(10)
                    pygame.display.flip()

                dt = clock.tick(fps) / 1000

                # ============= Game End ============ #
    except KeyboardInterrupt:
        pass
    finally:
        if client:
            client.disconnect()
            client_thread.join()
        if server:
            server.disconnect()
            server_thread.join()

if __name__ == "__main__":
    main()