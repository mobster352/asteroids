import pygame

import socket
import json
import time

from asteroid_peer import Asteroid_Peer

class Client():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.position = None
        self.rotation = 0
        self.peer_data = None
        self.run = True,
        self.num_connections = 0
        self.id = 0
        self.asteroids = []

    def connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            while self.run:
                try:
                    request = s.recv(8192)
                    if not request:
                        print("[Client] Server disconnected.")
                        break
                    decoded = json.loads(request.decode('utf-8'))
                    # print(f"[Client] Server says: {decoded}")
                    self.peer_data = decoded.get("peer_data")
                    self.num_connections = decoded.get("num_connections")

                    serialized_asteroids = decoded.get("asteroid_data")
                    if self.id == 1 and serialized_asteroids is not None:
                        # serialized_asteroids = [item for sublist in serialized_asteroids_nest for item in sublist]
                        # print(f"ASTEROID_DATA: {serialized_asteroids}")
                        self.asteroids = []
                        # print(f"serialized_asts: {serialized_asteroids}")
                        if serialized_asteroids is not None:
                            for a in serialized_asteroids:
                                if a != []:
                                    self.asteroids.append(Asteroid_Peer(
                                        pygame.Vector2(a.get("position_x"), a.get("position_y")),
                                        a.get("radius"), 
                                        # pygame.Vector2(a.get("velocity_x"), a.get("velocity_y"))
                                        ))
                                # print(f"SELF ASTS: {self.asteroids}")

                    action = self.peer_data.get("action")
                    if action == "get_position":
                        if self.id == 2:
                            serialized_asteroids = []
                            for a in self.asteroids:
                                if a != []:
                                    serialized_asteroids.append(
                                        {
                                            "position_x": a.position.x,
                                            "position_y": a.position.y,
                                            # "velocity_x": a.velocity.x,
                                            # "velocity_y": a.velocity.y,
                                            "radius": a.radius
                                        }
                                    )
                            data = {
                                "id": self.id,
                                "position": self.position, 
                                "rotation": self.rotation, 
                                "is_connected": True,
                                "asteroid_data": serialized_asteroids
                                }
                            # print(f"data: {data}")
                        else:
                            data = {
                                "id": self.id,
                                "position": self.position, 
                                "rotation": self.rotation, 
                                "is_connected": True
                                }
                        s.sendall(json.dumps(data).encode('utf-8'))
                        time.sleep(0.01)
                        # if self.id == 2:
                        #     self.asteroids = []
                except Exception as e:
                    print(f"[Client] Error: {e}")
                    break

    def update_position(self, position):
        self.position = (position.x, position.y)

    def update_rotation(self, rotation):
        self.rotation = rotation

    def kill_client(self):
        self.run = False