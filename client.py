import pygame

import socket
import json
import time
import threading

from asteroid_peer import Asteroid_Peer
from shot_peer import Shot_Peer

from constants import *

class Client():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        self.position = None
        self.rotation = 0
        self.peer_data = None
        self.run = True
        self.num_connections = 0
        self.id = 0
        self.asteroids = []
        self.peer_shots = []
        self.shots = []
        self.action = GET_ACTION
        self.destroy_asteroid_id = None
        self.is_server_alive = False

    def connect(self, lock):
        peer_shot_id = 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.client_socket = s
            s.settimeout(5.0)
            try:
                s.connect((self.host, self.port))
            except Exception as e:
                print(f"[Client] Connection failed: {e}")
                return 
            while self.run:
                try:
                    request = s.recv(8192)
                    if not request:
                        print("[Client] Server disconnected.")
                        break
                    decoded = json.loads(request.decode('utf-8'))
                    # print(f"[Client] Server says: {decoded}")
                    with lock:
                        decoded_action = decoded.get("action")
                        if decoded_action == GET_ACTION:
                            self.peer_data = decoded.get("peer_data")
                            self.num_connections = decoded.get("num_connections")

                            serialized_asteroids = decoded.get("asteroid_data")
                            if self.id == 1 and serialized_asteroids is not None:
                                self.asteroids = []
                                for a in serialized_asteroids:
                                    if a:
                                        self.asteroids.append(Asteroid_Peer(
                                            pygame.Vector2(a.get("position_x"), a.get("position_y")),
                                            a.get("radius"),
                                            a.get("asteroid_id")
                                            ))

                            if self.peer_data:
                                serialized_shots = self.peer_data.get("shots_data")
                                # print(f"[Client] shots_data: {serialized_shots}")
                                self.peer_shots = []
                                if serialized_shots is not None:
                                    # existing_peer_shot_ids = {shot.id for shot in self.peer_shots}
                                    for shot in serialized_shots:
                                        # if shot["id"] not in existing_peer_shot_ids:
                                        # if shot:
                                            self.peer_shots.append(
                                                Shot_Peer(
                                                    shot.get("position_x"),
                                                    shot.get("position_y"),
                                                    shot.get("radius"),
                                                    shot.get("id"),
                                                    shot.get("used")
                                                )
                                            )
                                            peer_shot_id += 1
                                    # print(f"Shot_Peers: {self.peer_shots}")
                        elif decoded_action == DESTROY_ACTION:
                            self.destroy_asteroid_id = decoded.get("destroy_asteroid_id")

                    if self.action == GET_ACTION:
                        if self.peer_data:
                            action = self.peer_data.get("action")
                            if action == "get_position":
                                serialized_shots = []
                                if self.shots is not None:
                                    for shot in self.shots:
                                        if shot:
                                            serialized_shots.append(
                                                {
                                                    "position_x": shot.position.x,
                                                    "position_y": shot.position.y,
                                                    "radius": shot.radius,
                                                    "id": shot.id,
                                                    "used": shot.used
                                                }
                                            )
                                if self.id == 2:
                                    serialized_asteroids = []
                                    for a in self.asteroids:
                                        if a:
                                            serialized_asteroids.append(
                                                {
                                                    "asteroid_id": a.id,
                                                    "position_x": a.position.x,
                                                    "position_y": a.position.y,
                                                    "radius": a.radius
                                                }
                                            )
                                    data = {
                                        "action": GET_ACTION,
                                        "id": self.id,
                                        "position": self.position, 
                                        "rotation": self.rotation, 
                                        "is_connected": True,
                                        "asteroid_data": serialized_asteroids,
                                        "shots_data": serialized_shots
                                        }
                                else:
                                    data = {
                                        "action": GET_ACTION,
                                        "id": self.id,
                                        "position": self.position, 
                                        "rotation": self.rotation, 
                                        "is_connected": True,
                                        "shots_data": serialized_shots
                                        }
                                s.sendall(json.dumps(data).encode('utf-8'))
                    elif self.action == DESTROY_ACTION:
                        data = {
                            "action": DESTROY_ACTION,
                            "destroy_asteroid_id": self.destroy_asteroid_id
                        }
                        s.sendall(json.dumps(data).encode('utf-8'))
                        self.action = GET_ACTION
                        self.destroy_asteroid_id = None

                    time.sleep(0.01) # 100 FPS?
                        # print(f"client.shots: {self.shots}")
                        # print(f"peer.shots: {self.peer_shots}")
                except socket.timeout:
                    continue
                except OSError:
                    break # socket was closed
                except Exception as e:
                    print(f"[Client] Error: {e}")
                    break

    def update_position(self, position):
        self.position = (position.x, position.y)

    def update_rotation(self, rotation):
        self.rotation = rotation

    def kill_client(self):
        self.run = False

    def destroy_asteroid(self, id):
        # print(f"DESTROY_SHOT: {id}")
        self.action = DESTROY_ACTION
        self.destroy_asteroid_id = id

    def disconnect(self):
        try:
            temp_socket = socket.create_connection((self.host, self.port), timeout=1)
            temp_socket.close()
        except:
            pass
        self.client_socket.close()
        print("Client Closed")

    def ping_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.client_socket = s
            s.settimeout(1.0)
            try:
                s.connect((self.host, self.port))
                self.is_server_alive = True
            except ConnectionRefusedError:
                print("Connection refused. Server might not be running.")