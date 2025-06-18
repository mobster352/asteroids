import pygame

import struct
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
        self.server_addr = (host, port)
        self.client_socket = None
        self.tcp_sock = None
        self.position = (0,0)
        self.rotation = 0
        self.peer_data = None
        self.run = True
        self.num_connections = 0
        self.id = 0
        self.asteroids = []
        self.peer_shots = []
        self.shots = []
        self.action = GET_ACTION
        self.destroy_asteroid_id = 0
        self.is_server_alive = False
        self.is_peer_connected = False
        self.peer_position = pygame.Vector2(0,0)
        self.peer_rotation = None
        self.is_connected = False


    def __run__(self, lock):
        while self.run:
            try:
                # self.process_json(lock)
                self.process_bytes(lock)
                # time.sleep(0.003) # 3 ms
                pygame.time.wait(100) # 100 ms
            except socket.timeout:
                continue
            except OSError as e:
                print(e)
                break # socket was closed
            except Exception as e:
                print(f"[Client] Error: {e}")
                break

    def connect(self, lock):
        if self.is_server_alive:
            self.__run__(lock)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.client_socket_tcp = s
            self.client_socket_tcp.settimeout(30.0)
            try:
                self.client_socket_tcp.connect((self.host, self.port))
                self.is_server_alive = True
            except Exception as e:
                print(f"[Client] Connection failed: {e}")
                return 
            self.__run__(lock)         

    def update_position(self, position):
        self.position = (position.x, position.y)

    def update_rotation(self, rotation):
        self.rotation = rotation

    def kill_client(self):
        self.run = False

    def destroy_asteroid(self, id):
        self.destroy_asteroid_id = id

    def disconnect(self):
        try:
            temp_socket = socket.create_connection((self.host, self.port), timeout=1)
            temp_socket.close()
        except ConnectionRefusedError:
            print("Connection refused. Server might not be running.")
        finally:
            self.tcp_sock.close()
            print("[Client] TCP Socket Closed")

    def ping_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(30.0)
        try:
            self.client_socket.connect((self.host, self.port))
            self.is_server_alive = True
        except ConnectionRefusedError:
            print("Connection refused. Server might not be running.")
        except Exception as e:
            print(f"Exception: {e}")

# PROCESS JSON using TCP
    def recvall(self, n):
        # """Helper to receive exactly n bytes or return None if connection closed."""
        data = b''
        while len(data) < n:
            packet = self.client_socket.recv(n - len(data))
            if not packet:
                return None  # connection closed
            data += packet
        return data

    def recv_json_message(self):
        # """Receive a single length-prefixed JSON message."""
        raw_len = self.recvall(4)
        if not raw_len:
            return None  # connection closed or no data
        msg_len = struct.unpack('!I', raw_len)[0]  # network byte order

        print(f"msg_len: {msg_len}")
        raw_msg = self.recvall(msg_len)
        if not raw_msg:
            return None  # connection closed during message receive

        return json.loads(raw_msg)

    def send_json(self, data):
        message = json.dumps(data).encode('utf-8')
        length = struct.pack('!I', len(message))
        self.client_socket.sendall(length + message)

    def handle_message_json(self, data):
        decoded_action = data.get("action")
        if decoded_action == GET_ACTION:
            self.peer_data = data.get("peer_data")
            self.num_connections = data.get("num_connections")

            if self.peer_data:
                self.is_peer_connected = self.peer_data.get("is_connected")
                self.peer_position = self.peer_data.get("position")
                self.peer_rotation = self.peer_data.get("rotation")

            serialized_asteroids = data.get("asteroid_data")
            if self.id == 2 and serialized_asteroids is not None:
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
                self.peer_shots = []
                if serialized_shots is not None:
                    # existing_peer_shot_ids = {shot.id for shot in self.peer_shots}
                    for shot in serialized_shots:
                            self.peer_shots.append(
                                Shot_Peer(
                                    shot.get("position_x"),
                                    shot.get("position_y"),
                                    shot.get("radius"),
                                    shot.get("id"),
                                    shot.get("used")
                                )
                            )
        elif decoded_action == DESTROY_ACTION:
            self.destroy_asteroid_id = data.get("destroy_asteroid_id")

    def build_message_json(self):
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
                    if self.id == 1:
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
                    # self.client_socket.sendall(json.dumps(data).encode('utf-8'))
                    self.send_json(data)
        elif self.action == DESTROY_ACTION:
            data = {
                "action": DESTROY_ACTION,
                "destroy_asteroid_id": self.destroy_asteroid_id
            }
            # self.client_socket.sendall(json.dumps(data).encode('utf-8'))
            self.send_json(data)
            self.action = GET_ACTION
            self.destroy_asteroid_id = None

    def process_json(self, lock):
        decoded = self.recv_json_message()
        if decoded is None:
            raise OSError("[Client] Server disconnected.")
        with lock:
            self.handle_message_json(decoded)
            self.build_message_json()

# PROCESS BYTES using TCP
    def build_action_message(self):
        action_data = struct.pack(ACTION_STRUCT, self.action)
        msg = struct.pack(MSG_HEADER, len(action_data) + 1, MSG_TYPE_ACTION) + action_data
        return msg

    def build_client_message(self):
        client_data = struct.pack(CLIENT_STRUCT, self.id, True)
        msg = struct.pack(MSG_HEADER, len(client_data) + 1, MSG_TYPE_CLIENT) + client_data
        return msg

    def build_player_message(self):
        player_data = struct.pack(PLAYER_STRUCT, self.position[0], self.position[1], self.rotation)
        msg = struct.pack(MSG_HEADER, len(player_data) + 1, MSG_TYPE_PLAYER) + player_data
        return msg

    def build_asteroid_message(self):
        asteroid_data = b''
        for a in self.asteroids:
            asteroid_data += struct.pack(ASTEROID_STRUCT, a.id, a.position.x, a.position.y, a.radius)
        msg = struct.pack(MSG_HEADER, len(asteroid_data) + 1, MSG_TYPE_ASTEROID) + asteroid_data
        return msg

    def build_shot_message(self):
        shot_data = b''
        for s in self.shots:
            shot_data += struct.pack(SHOT_STRUCT, s.id[0], s.position.x, s.position.y, s.radius, s.used)
        msg = struct.pack(MSG_HEADER, len(shot_data) + 1, MSG_TYPE_SHOT) + shot_data
        return msg

    def build_destroy_asteroid_message(self):
        destroy_asteroid_data = struct.pack(DESTROY_ASTEROID_STRUCT, self.destroy_asteroid_id)
        msg = struct.pack(MSG_HEADER, len(destroy_asteroid_data) + 1, MSG_TYPE_DESTROY_ASTEROID) + destroy_asteroid_data
        return msg

    def send_game_state(self):
        if self.action == GET_ACTION:
            msg1 = self.build_action_message()
            msg2 = self.build_client_message()
            msg3 = self.build_player_message()
            if self.shots is not None:
                msg5 = self.build_shot_message()
            else:
                msg5 = b''
            if self.id == 1 and self.asteroids is not None:
                msg4 = self.build_asteroid_message()
                self.client_socket.sendall(msg1 + msg2 + msg3 + msg4 + msg5)  # Send all messages in one TCP packet
            else:
                self.client_socket.sendall(msg1 + msg2 + msg3 + msg5)  # Send all messages in one TCP packet
        elif self.action == DESTROY_ACTION:
            msg1 = self.build_destroy_asteroid_message()
            self.client_socket.sendall(msg1)
            self.action = GET_ACTION
            self.destroy_asteroid_id = None
        else:
            print(f"[Client] invalid action: {self.action}")

    def handle_message(self, msg_type, payload, lock):
        with lock:
            if msg_type == MSG_TYPE_ACTION:
                self.action = struct.unpack(ACTION_STRUCT, payload)[0]

            elif msg_type == MSG_TYPE_SERVER_DATA:
                self.num_connections = struct.unpack(SERVER_DATA_STRUCT, payload)[0]

            elif msg_type == MSG_TYPE_CLIENT:
                id, is_peer_connected = struct.unpack(CLIENT_STRUCT, payload)
                # print(f"[Client] id: {id}, is_peer_connected: {is_peer_connected}")
                self.id = id 
                self.is_peer_connected = is_peer_connected

            elif msg_type == MSG_TYPE_PLAYER:
                self.peer_position.x, self.peer_position.y, self.peer_rotation = struct.unpack(PLAYER_STRUCT, payload)

            elif msg_type == MSG_TYPE_ASTEROID:
                size = struct.calcsize(ASTEROID_STRUCT)
                if self.id == 2 and size > 0:
                    self.asteroids = []
                    for i in range(0, len(payload), size):
                        id, x, y, radius = struct.unpack(ASTEROID_STRUCT, payload[i:i+size])
                        self.asteroids.append(Asteroid_Peer(pygame.Vector2(x, y),radius,id))

            elif msg_type == MSG_TYPE_SHOT:
                size = struct.calcsize(SHOT_STRUCT)
                if size > 0:
                    self.peer_shots = []
                    for i in range(0, len(payload), size):
                        id, x, y, radius, used = struct.unpack(SHOT_STRUCT, payload[i:i+size])
                        self.peer_shots.append(Shot_Peer(x,y,radius,id,used))

            elif msg_type == MSG_TYPE_DESTROY_ASTEROID:
                self.destroy_asteroid_id = struct.unpack(DESTROY_ASTEROID_STRUCT, payload)[0]

            elif msg_type == MSG_TYPE_PING:
                self.is_server_alive = struct.unpack(PING_STRUCT, payload)[0]

    def process_bytes(self, lock):
        buffer = b''
        data = self.client_socket.recv(4096)
        if not data:
            # print("[Client] end of packet")
            return
        print(f"[Client] data_len: {len(data)}")
        buffer += data
        print(f"[Client] buffer_len: {len(buffer)}")
        while True:
            if len(buffer) < 5:
                # print(f"[Client] len(buffer) < 5")
                break  # wait for full header

            # B is char is message type (ie which object it is)
            msg_len, msg_type = struct.unpack('!IB', buffer[:5])
            total_len = 5 + (msg_len - 1)

            if len(buffer) < total_len:
                # print(f"[Client] buffer done")
                break  # wait for full payload

            payload = buffer[5:total_len]
            self.handle_message(msg_type, payload)
            buffer = buffer[total_len:]
        self.send_game_state()

    # UDP
    def send_heartbeat(self, lock):
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.settimeout(2.5)
        self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_sock.connect((self.host, self.port))
        self.is_connected = True
        while self.is_connected:
            try:
                self.tcp_sock.sendall(b'heartbeat')
                data = self.tcp_sock.recv(1024)
                self.process_bytes_udp(data, lock)
                # print(f"[Client] client_id: {self.id}")
                time.sleep(1) # 1 second
                # pygame.time.wait(1000) # 1 second
            except Exception as e:
                print(f"[CLIENT] TCP connection lost: {e}")
                break
        print(f"[Client] TCP Socket Closed")
        self.tcp_sock.close()

    def build_ping_message(self):
        ping_data = struct.pack(PING_STRUCT, self.is_server_alive)
        msg = struct.pack(MSG_HEADER, len(ping_data) + 1, MSG_TYPE_PING) + ping_data
        return msg

    def send_game_state_udp(self):
        if self.action == GET_ACTION:
            msg1 = self.build_action_message()
            msg2 = self.build_client_message()
            msg3 = self.build_player_message()
            msg4 = b''
            msg5 = b''
            msg7 = b''
            if self.shots is not None:
                msg5 = self.build_shot_message()
            if self.id == 1 and len(self.asteroids) > 0:
                msg4 = self.build_asteroid_message()
            if self.id == 2 and self.destroy_asteroid_id > 0:
                msg7 = self.build_destroy_asteroid_message()
                self.destroy_asteroid_id = 0
            return msg2 + msg1 + msg3 + msg5 + msg4 + msg7
        else:
            raise Exception(f"[Client] invalid action: {self.action}")

    def connect_udp(self, lock):
        while self.run:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                self.client_socket = s
                self.client_socket.settimeout(2.5)
                try:
                    if self.is_server_alive:
                        msg = self.send_game_state_udp()
                    else:
                        msg = self.build_ping_message()
                    self.client_socket.sendto(msg, self.server_addr)

                    data, addr = self.client_socket.recvfrom(4096)
                    self.process_bytes_udp(data, lock)
                    time.sleep(0.01) # 10 ms
                    # pygame.time.wait(10) # 10 ms
                except socket.timeout:
                    print(f"[Client] socket.timeout")
                    break # no data received
                except OSError as e:
                    print(f"[Client] OSError: {e}")
                    break # socket was closed
                except Exception as e:
                    print(f"[Client] Error: {e}")
                    break

    def process_bytes_udp(self, data, lock):
        buffer = b''
        if not data: #or addr != self.server_addr:
            print("[Client] end of packet")
            return
        # print(f"data_len: {len(data)}")
        buffer += data
        # print(f"buffer_len: {len(buffer)}")
        while True:
            if len(buffer) < 5:
                # print(f"[Client] len(buffer) < 5")
                break  # wait for full header
            msg_len, msg_type = struct.unpack('!IB', buffer[:5])
            total_len = 5 + (msg_len - 1)

            if len(buffer) < total_len:
                # print(f"[Client] buffer done")
                break  # wait for full payload\
            payload = buffer[5:total_len]
            self.handle_message(msg_type, payload, lock)
            buffer = buffer[total_len:]

    def disconnect_udp(self):
        self.is_connected = False
        self.run = False
        # self.client_socket.close()
        print("[Client] Client Closed")
