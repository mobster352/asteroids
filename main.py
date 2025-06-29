import pygame
import pygame.freetype
import pygame_textinput
import pygame.locals as pl

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
from textbox import Textbox

import re

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
            client.id = 2
        else:
            player = Player(screen_width / 2 - 100, screen_height / 2, "cyan")
            client.id = 1

            AsteroidField.containers = (updatable,)
            asteroid_field = AsteroidField(screen_width, screen_height)
            client.asteroids = asteroid_field.asteroids

    peer = Peer(screen_width / 2, screen_height / 2, "teal")

    ui = UI(0, 0)

    return player, ui, peer, asteroid_field

def game_over(asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game, client_heartbeat):
    if ENABLE_SOUNDS:
        pygame.mixer.Sound(SHIP_EXPLOSION).play()
    print("Game Over!")
    asteroids.empty()
    shots.empty()
    updatable.empty()
    drawable.empty()
    if client:
        client.disconnect_udp()
        print("[Client] client disconnected")
        if client_thread:
            client_thread.join(1)
            print("[Client] client thread joined")
        if client_heartbeat:
            client_heartbeat.join(1)
            print("[Client] client heartbeat joined")
    if server:
        server.disconnect_udp(client.id)
        print("[Client] server disconnected")
        if server_thread:
            server_thread.join(1)
            print("[Client] server thread joined")
        server = None
    client = None
    player = None
    peer = None
    start_game = False
    return asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game

def leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu):
    print("Left game")

    # reset game state
    host_input_active = True
    player = None
    peer = None

    start_game = False
    connect_pressed = False
    is_game_over = False
    is_alive = True

    menu = IN_MENU
    # menu = None

    return host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu

def show_mouse_pos(font, dynamic_screen_width, dynamic_screen_height, screen):
    mouse_pos = pygame.mouse.get_pos()
    mouse_pos_surface, rect = font.render(f"{mouse_pos}", "white", (0,0,0))
    rect_width = rect[2]
    rect_height = rect[3]
    screen.blit(mouse_pos_surface, (dynamic_screen_width - rect_width, dynamic_screen_height - rect_height))

def show_game_over(font, dynamic_screen_width, dynamic_screen_height, screen, text):
    mouse_pos_surface, rect = font.render(text, "white", (0,0,0))
    rect_width = rect[2] / 2
    rect_height = rect[3] / 2
    screen.blit(mouse_pos_surface, (dynamic_screen_width / 2 - rect_width, dynamic_screen_height / 4 - rect_height))

def main():
    bg = pygame.image.load(BACKGROUND_IMAGE)
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    print("Starting Asteroids!")
    # print(f"Screen width: {SCREEN_WIDTH}")
    # print(f"Screen height: {SCREEN_HEIGHT}")

    pygame.init()

    pygame.key.set_repeat(200, 25)
    
    if ENABLE_SOUNDS:
        pygame.mixer.init()

    info = pygame.display.Info()
    # SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h

    # screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME | pygame.SCALED | pygame.FULLSCREEN) # fullscreen mode
    # screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME | pygame.SCALED) # borderless windowed mode
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) # windowed mode
    pygame.display.set_caption("Asteroids")
    # pygame.display.toggle_fullscreen()
    clock = pygame.time.Clock()
    dt = 0
    fps = 60

    font = pygame.freetype.Font(os.path.realpath(FONT_FILE), 30)
    menu_font = pygame.freetype.Font(os.path.realpath(FONT_FILE), 80)
    filename = os.path.abspath(SAVE_FILE)

    regex = r"^[.0-9]*$" # Only digits and . (0.0.0.0)

    host_manager = pygame_textinput.TextInputManager(validator = lambda input: len(input) <= 14 and re.match(regex, input) or input == "")
    port_manager = pygame_textinput.TextInputManager(validator = lambda input: len(input) <= 5 and input.isdigit() or input == "")

    host_input = pygame_textinput.TextInputVisualizer(manager=host_manager)
    port_input = pygame_textinput.TextInputVisualizer(manager=port_manager)

    # host_input.value = '0.0.0.0'
    # port_input.value = '65432'

    host_input_active = True

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
    client_heartbeat = None

    menu = IN_MENU
    start_game = False
    connect_pressed = False
    is_game_over = False
    is_alive = True

    new_game_button = Button("New Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    join_room_button = Button("Join Room", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    quit_game_button = Button("Quit Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 1.65)

    multiplayer_button = Button("Multiplayer", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    create_room_button = Button("Create Room", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    main_menu_button = Button("Main Menu", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 1.3)

    connect_button = Button("Connect", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 1.5)

    host_textbox = Textbox("Host", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2.5)

    port_textbox = Textbox("Port", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

    leave_game_button = Button("Leave Game", SCREEN_WIDTH, SCREEN_HEIGHT, 2, 2)

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

                # ========== Main Menu Start ============ #

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

                screen.fill("black")
                screen.blit(bg, (0,0))

                # show_mouse_pos(font, dynamic_screen_width, dynamic_screen_height, screen)

                menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
                # rect - (x, y, w, h)

                rect_width_center = rect[2] / 2
                rect_height_center = rect[3] / 2

                screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

                new_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                new_game_button.draw_button("white", "blue", font, screen)

                multiplayer_button.update_button(dynamic_screen_width, dynamic_screen_height)
                multiplayer_button.draw_button("white", "blue", font, screen)

                quit_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                quit_game_button.draw_button("white", "red", font, screen)

                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ========== Main Menu End ========== #

            elif menu == IN_MULTIPLAYER_MENU:

                # ========== Multiplayer Menu Start ============ #

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if create_room_button.check_collisions(mouse_pos):
                            menu = IN_CREATE_ROOM_MENU                                                
                        elif join_room_button.check_collisions(mouse_pos):
                            menu = IN_JOIN_ROOM_MENU
                        elif main_menu_button.check_collisions(mouse_pos):
                            menu = IN_MENU

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

            elif menu == IN_CREATE_ROOM_MENU:

                if client:
                    if client.num_connections == -1:
                        menu = IN_MENU
                        client = None
                    elif client.num_connections == 2:
                        menu = IN_MULTIPLAYER_GAME
                        connect_pressed = False
                
                # ========== Create Room Menu Start ============ #

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if connect_button.check_collisions(mouse_pos) and (host_input.value != "" and port_input.value != ""):
                            server = Server(host_input.value, int(port_input.value))
                            server_thread = threading.Thread(target=server.start_server_udp, daemon=True).start()
                            time.sleep(0.01) # 10 ms

                            client = Client(host_input.value, int(port_input.value))

                            client_heartbeat = threading.Thread(target=client.send_heartbeat, args=(lock,))
                            client_heartbeat.daemon = True
                            client_heartbeat.start()
                            time.sleep(0.01) # 10 ms

                            client_thread = threading.Thread(target=client.connect_udp, args=(lock,))
                            client_thread.daemon = True
                            client_thread.start()

                            time.sleep(0.01) # 10 ms

                            player, ui, peer, asteroid_field = setup_multiplayer_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename, client)     
                            connect_pressed = True
                        elif host_textbox.check_collisions(mouse_pos):
                            host_input_active = True   
                        elif port_textbox.check_collisions(mouse_pos):
                            host_input_active = False           
                        elif main_menu_button.check_collisions(mouse_pos):
                            menu = IN_MENU
                            if client:
                                client.kill_client()
                                client.disconnect_udp()
                            if server:
                                server.disconnect_udp(client.id)
                                server = None
                            client = None
                            player = None
                            peer = None

                screen.fill("black")
                screen.blit(bg, (0,0))

                menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
                # rect - (x, y, w, h)

                rect_width_center = rect[2] / 2
                rect_height_center = rect[3] / 2

                screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

                if connect_pressed:
                    connection_surface, rect = font.render(f"Waiting for connection on {host_input.value}:{port_input.value}...", "white", (0,0,0))
                    rect_width = rect[2] / 2
                    rect_height = rect[3]
                    screen.blit(connection_surface, (dynamic_screen_width / 2 - rect_width, dynamic_screen_height / 2 - rect_height))
                else:
                    host_textbox.update_textbox(dynamic_screen_width, dynamic_screen_height)
                    x_pos, y_pos = host_textbox.draw_textbox("white", "grey", font, screen)

                    host_input.font_color = "black"
                    if host_input_active:
                        host_input.update(event_list)
                        port_input.cursor_visible = False
                    screen.blit(host_input.surface, (x_pos, y_pos))

                    port_textbox.update_textbox(dynamic_screen_width, dynamic_screen_height)
                    x_pos, y_pos = port_textbox.draw_textbox("white", "grey", font, screen)

                    port_input.font_color = "black"
                    if not host_input_active:
                        port_input.update(event_list)
                        host_input.cursor_visible = False
                    screen.blit(port_input.surface, (x_pos, y_pos))

                connect_button.update_button(dynamic_screen_width, dynamic_screen_height)
                connect_button.draw_button("white", "blue", font, screen)

                main_menu_button.update_button(dynamic_screen_width, dynamic_screen_height)
                main_menu_button.draw_button("white", "blue", font, screen)

                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ========== Create Room Menu End ========== #

            elif menu == IN_JOIN_ROOM_MENU:

                if client:
                    if client.num_connections == -1:
                        menu = IN_MENU
                        client = None
                    elif client.num_connections == 2:
                        menu = IN_MULTIPLAYER_GAME
                        connect_pressed = False

                # ========== Join Room Start ============ #

                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()                                              
                        if connect_button.check_collisions(mouse_pos):
                            try:
                                client = Client(host_input.value, int(port_input.value))
                                
                                client_heartbeat = threading.Thread(target=client.send_heartbeat, args=(lock,))
                                client_heartbeat.daemon = True
                                client_heartbeat.start()
                                time.sleep(0.01) # 10 ms

                                client_thread = threading.Thread(target=client.connect_udp, args=(lock,))
                                client_thread.daemon = True
                                client_thread.start()

                                time.sleep(0.1) # 10 ms

                                player, ui, peer, asteroid_field = setup_multiplayer_game(updatable, drawable, asteroids, shots, dynamic_screen_width, dynamic_screen_height, filename, client)
                                connect_pressed = True
                            except Exception as e:
                                print(f"[Client] Server not alive: {e}")
                        elif host_textbox.check_collisions(mouse_pos):
                            host_input_active = True   
                        elif port_textbox.check_collisions(mouse_pos):
                            host_input_active = False 
                        elif main_menu_button.check_collisions(mouse_pos):
                            menu = IN_MENU
                            if client:
                                client.kill_client()
                                client.disconnect_udp()
                                client = None
                            player = None
                            peer = None

                screen.fill("black")
                screen.blit(bg, (0,0))

                menu_surface, rect = menu_font.render("Asteroids", "white", (0,0,0))
                # rect - (x, y, w, h)

                rect_width_center = rect[2] / 2
                rect_height_center = rect[3] / 2

                screen.blit(menu_surface, (dynamic_screen_width / 2 - rect_width_center, dynamic_screen_height / 4 - rect_height_center))

                if connect_pressed:
                    connection_surface, rect = font.render(f"Failed to join connection on {host_input.value}:{port_input.value}", "white", (0,0,0))
                    rect_width = rect[2] / 2
                    rect_height = rect[3]
                    screen.blit(connection_surface, (dynamic_screen_width / 2 - rect_width, dynamic_screen_height / 2 - rect_height))
                else:
                    host_textbox.update_textbox(dynamic_screen_width, dynamic_screen_height)
                    x_pos, y_pos = host_textbox.draw_textbox("white", "grey", font, screen)

                    host_input.font_color = "black"
                    if host_input_active:
                        host_input.update(event_list)
                        port_input.cursor_visible = False
                    screen.blit(host_input.surface, (x_pos, y_pos))

                    port_textbox.update_textbox(dynamic_screen_width, dynamic_screen_height)
                    x_pos, y_pos = port_textbox.draw_textbox("white", "grey", font, screen)

                    port_input.font_color = "black"
                    if not host_input_active:
                        port_input.update(event_list)
                        host_input.cursor_visible = False
                    screen.blit(port_input.surface, (x_pos, y_pos))

                connect_button.update_button(dynamic_screen_width, dynamic_screen_height)
                connect_button.draw_button("white", "blue", font, screen)

                main_menu_button.update_button(dynamic_screen_width, dynamic_screen_height)
                main_menu_button.draw_button("white", "blue", font, screen)

                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ========== Join Room End ========== #

            elif menu == IN_MULTIPLAYER_GAME:
                if client and client.num_connections == 2:
                    if not client.is_peer_connected:
                        client.num_connections = 1
                        continue
                    else:
                        start_game = True

                    # ========== Multiplayer Game Start ========== #

                    for event in event_list:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            mouse_pos = pygame.mouse.get_pos()
                            if player:
                                if player.pause and leave_game_button.check_collisions(mouse_pos):
                                    asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game = game_over(
                                        asteroids, 
                                        shots, 
                                        updatable, 
                                        drawable, 
                                        client, 
                                        client_thread, 
                                        player, 
                                        peer, 
                                        server, 
                                        server_thread, 
                                        start_game, 
                                        client_heartbeat
                                        )
                                    is_game_over = True
                                    host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu = leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu)
                                    start_game = False
                                elif is_game_over and leave_game_button.check_collisions(mouse_pos):
                                    host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu = leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu)
                                    start_game = False

                    if not start_game:
                        continue

                    screen.fill("black")
                    screen.blit(bg, (0,0))

                    # ======== UI START =========== #

                    score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
                    screen.blit(score_surface, (20, 10))

                    # ======== UI END =========== #

                    with lock:
                        if client.id == 2:
                            for s in client.shots:
                                if s.alive():
                                    if s.used:
                                        s.kill()

                        shots.empty()
                        shots.add(*[s for s in client.shots if s.alive()])
                        
                        shots.add(*[s for s in client.peer_shots if s.alive()])
                        asteroids.empty()
                        asteroids.add(*[a for a in client.asteroids if a.alive()])

                    updatable.update(dt, dynamic_screen_width, dynamic_screen_height)
                    for d in drawable:
                        d.draw(screen)

                    if client.id == 2:
                        for a in client.asteroids:
                            if not a.alive():
                                continue
                            a.draw_peer(screen)

                    if client.peer_shots:
                        for s in client.peer_shots:
                            if not s.alive():
                                continue
                            s.draw_peer(screen)
                                
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
                            if a.id == client.destroy_asteroid_id and client.id == 1:
                                client.asteroids = a.split(asteroid_field)
                                client.destroy_asteroid_id = None
                                continue
                        for a in client.asteroids:
                            if not a.alive():
                                continue
                            if a.check_collisions(player):
                                asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game = game_over(
                                asteroids, 
                                shots, 
                                updatable, 
                                drawable, 
                                client, 
                                client_thread, 
                                player, 
                                peer, 
                                server, 
                                server_thread, 
                                start_game, 
                                client_heartbeat
                                )
                                is_game_over = True
                                is_alive = False
                                break
                            for s in player.get_shots():
                                if not s.alive():
                                    continue
                                if a.check_collisions(s):
                                    hit = True
                                    # print(f"[Client] {client.id} hit {a.id}")
                                    if client.id == 1:
                                        client.asteroids = a.split(asteroid_field)
                                        s.used = True                                
                                        if isinstance(s, Shot_Peer):
                                            if client.peer_shots:
                                                if s in client.peer_shots:
                                                    client.peer_shots.remove(s)
                                        else:
                                            if client.shots:
                                                if s in client.shots:
                                                    client.shots.remove(s)
                                            if s in player.shots:
                                                s.kill_shot(player.shots)
                                            ui.update_score(10)
                                        s.kill()
                                        break
                                    else:
                                        ui.update_score(10)
                                        client.destroy_asteroid(a.id)
                                        s.kill()
                                        break
                            if hit:
                                break

                        if player:
                            # update client
                            client.update_position(player.get_position())
                            client.update_rotation(player.get_rotation())
                            
                            # update peer
                            if client.is_peer_connected:
                                peer.update_position(client.peer_position)
                                peer.update_rotation(client.peer_rotation)
                                peer.draw_peer(screen)

                        if player:
                            if player.pause:
                                leave_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                                leave_game_button.draw_button("white", "red", font, screen)

                    # ========== Multiplayer Game End ========== #         
                elif client and client.num_connections == 1 and start_game:
                    with lock:
                        asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game = game_over(
                            asteroids, 
                            shots, 
                            updatable, 
                            drawable, 
                            client, 
                            client_thread, 
                            player, 
                            peer, 
                            server, 
                            server_thread, 
                            start_game, 
                            client_heartbeat
                            )
                        is_game_over = True
                elif is_game_over:
                    for event in event_list:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            mouse_pos = pygame.mouse.get_pos()
                            if is_game_over and leave_game_button.check_collisions(mouse_pos):
                                host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu = leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu)
                                start_game = False
                                is_game_over = False
                    if is_alive:
                        game_over_text = "You Win!"
                    else:
                        game_over_text = "You Lose!"
                    show_game_over(menu_font, dynamic_screen_width, dynamic_screen_height, screen, game_over_text)
                    leave_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                    leave_game_button.draw_button("white", "red", font, screen)
                else:
                    pass
                pygame.display.flip()
                dt = clock.tick(fps) / 1000
            
            elif menu is None:
                break

            else:
                start_game = True
                for event in event_list:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if quit_game_button.check_collisions(mouse_pos):
                            run = False
                        elif player:
                            if player.pause and leave_game_button.check_collisions(mouse_pos):
                                asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game = game_over(
                                asteroids, 
                                shots, 
                                updatable, 
                                drawable, 
                                client, 
                                client_thread, 
                                player, 
                                peer, 
                                server, 
                                server_thread, 
                                start_game, 
                                client_heartbeat
                                )
                                host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu = leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu)
                                start_game = False
                                is_game_over = False
                            elif is_game_over and leave_game_button.check_collisions(mouse_pos):
                                asteroids, shots, updatable, drawable, client, client_thread, player, peer, server, server_thread, start_game = game_over(
                                asteroids, 
                                shots, 
                                updatable, 
                                drawable, 
                                client, 
                                client_thread, 
                                player, 
                                peer, 
                                server, 
                                server_thread, 
                                start_game, 
                                client_heartbeat
                                )
                                host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu = leave_game(host_input_active, player, peer, start_game, connect_pressed, is_game_over, is_alive, menu)
                                start_game = False
                                is_game_over = False

                if not start_game:
                    continue

                # ========== Game Start ========= #
                
                screen.fill("black")
                screen.blit(bg, (0,0))

                # ======== UI START =========== #

                score_surface, rect = font.render(f"Score: {ui.get_score()}", "white", (0,0,0))
                screen.blit(score_surface, (20, 10))

                score_surface, rect = font.render(f"High Score: {ui.get_high_score()}", "white", (0,0,0))
                screen.blit(score_surface, (200, 10))

                # ======== UI END =========== #

                if player:
                    if player.pause:
                        leave_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                        leave_game_button.draw_button("white", "red", font, screen)
                    elif is_game_over:
                        show_game_over(menu_font, dynamic_screen_width, dynamic_screen_height, screen, "Game Over!")
                        leave_game_button.update_button(dynamic_screen_width, dynamic_screen_height)
                        leave_game_button.draw_button("white", "red", font, screen)
                    else:
                        updatable.update(dt, dynamic_screen_width, dynamic_screen_height)
                        for d in drawable:
                            d.draw(screen)

                        for a in asteroids:
                            if a.check_collisions(player):
                                is_game_over = True
                                # Save data
                                if ui.get_high_score() < ui.get_score():
                                    ui.update_high_score(ui.get_score())
                                    with open(filename, "wb") as f:
                                        data = {"high_score": ui.get_high_score()}
                                        pickle.dump(data, f)
                                break
                            for s in shots:
                                if a.check_collisions(s):
                                    a.split(asteroid_field)
                                    s.kill()
                                    ui.update_score(10)
                    
                pygame.display.flip()
                dt = clock.tick(fps) / 1000

                # ============= Game End ============ #

    except KeyboardInterrupt:
        pass
    finally:
        pass

if __name__ == "__main__":
    main()