import struct
import socket
import threading
import time
import json

from constants import *

from datetime import datetime

class Client_Data():
    def __init__(self):
        self.conn_addr = None  # (conn, addr)
        self.position = (0, 0)
        self.rotation = 0
        self.is_connected = False,
        self.asteroid_data = [],
        self.id = 0
        self.shots_data = []

        self.action = GET_ACTION
        self.destroy_asteroid_id = None

        # UDP
        self.addr = (None,None) # (ip, port)
        self.last_seen = None # last time packet received

    def update_data(self, decoded_json):
        self.position = decoded_json.get("position")
        self.rotation = decoded_json.get("rotation")
        self.is_connected = decoded_json.get("is_connected")
        self.asteroid_data = decoded_json.get("asteroid_data")
        self.id = decoded_json.get("id")
        self.shots_data = decoded_json.get("shots_data")

    def reset_data(self):
        self.conn_addr = (None, None)
        self.position = (0,0)
        self.rotation = 0
        self.is_connected = False
        self.asteroid_data = []
        self.id = 0
        self.shots_data = []
        self.last_seen = None

class Server():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.num_connections = 0
        self.server_socket = None
        # Shared state
        self.clients = [Client_Data(), Client_Data()]
        self.lock = threading.Lock()

    def start_server(self):
        # print("Local IP address:", self.get_local_ip())
        # print("Local IP address (filtered):", self.get_local_ip_filtered())
        # Main server loop
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.server_socket = s
            s.settimeout(30.0)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port}...")

            while True:
                try:
                    conn, addr = s.accept()
                    slot = self.find_free_slot()
                    if slot is None:
                        print("[!] Connection refused: max clients reached")
                        conn.close()
                        continue
                    with self.lock:
                        self.clients[slot].conn_addr = (conn, addr)
                    thread = threading.Thread(target=self.handle_client, args=(conn, addr, slot), daemon=True)
                    thread.start()
                except socket.timeout:
                    continue
                except OSError:
                    break # socket was closed

    def build_request(self, client, other_client):
        if client.id == 2:
            # print(f"OTHER_ASTS: {other_client.asteroid_data}")
            return {
                "action": GET_ACTION,
                "peer_data": {
                "action": "get_position", 
                "position": other_client.position, 
                "rotation": other_client.rotation, 
                "is_connected": other_client.is_connected,
                "shots_data": other_client.shots_data
                },
                "num_connections": self.num_connections,
                "asteroid_data": other_client.asteroid_data
            }
        else:
            return {
                "action": GET_ACTION,
                "peer_data": {
                "action": "get_position", 
                "position": other_client.position, 
                "rotation": other_client.rotation, 
                "is_connected": other_client.is_connected,
                "shots_data": other_client.shots_data
                },
                "num_connections": self.num_connections
            }

    def handle_client(self, conn, addr, index):
        print(f"[+] Client {index+1} connected: {addr}")
        try:
            while True:
                other_index = 1 - index
                try:
                    # self.process_json(conn, index, other_index)    
                    self.process_bytes(conn, index, other_index)   
                except OSError as e:
                    print(e)
                    break # socket was closed
                except (BrokenPipeError, ConnectionResetError) as e:
                    print(f"[!] Client {index+1} send error: {e}")
                    break
                except Exception as e:
                    print(f"[!] Error receiving from Client {index+1}: {e}")
                    break
                time.sleep(0.003)  # Reduce CPU usage
        finally:
            with self.lock:
                self.clients[index].reset_data()
                self.num_connections -= 1
                print(f"[x] Client {index+1} cleanup done.")
            conn.close()

    def find_free_slot(self):
        with self.lock:
            for i in range(MAX_CONNECTIONS):
                if self.clients[i].conn_addr is None:
                    self.num_connections += 1
                    return i
        return None

    def get_local_ip(self):
        host = socket.gethostname()  # Get the hostname
        local_ip = socket.gethostbyname(host)  # Resolve hostname to IP
        return local_ip

    def get_local_ip_filtered(self):
        local_hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(local_hostname)[2]
        # Filter out loopback addresses
        filtered_ips = [ip for ip in ip_addresses if not ip.startswith("127.")]
        return filtered_ips[0] if filtered_ips else None

    def disconnect(self):
        try:
            temp_socket = socket.create_connection((self.host, self.port), timeout=1)
            temp_socket.close()
        except ConnectionRefusedError:
            print("Connection refused.")
        finally:
            self.server_socket.close()
            print("Server closed")

    # PROCESS JSON using TCP
    def send_json(self, sock, data):
        message = json.dumps(data).encode('utf-8')
        length = struct.pack('!I', len(message))
        sock.sendall(length + message)

    def recvall(self, sock, n):
        # """Helper to receive exactly n bytes or return None if connection closed."""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None  # connection closed
            data += packet
        return data

    def recv_json_message(self, sock):
        # """Receive a single length-prefixed JSON message."""
        raw_len = self.recvall(sock, 4)
        if not raw_len:
            return None  # connection closed or no data
        msg_len = struct.unpack('!I', raw_len)[0]  # network byte order

        raw_msg = self.recvall(sock, msg_len)
        if not raw_msg:
            return None  # connection closed during message receive

        return json.loads(raw_msg)

    def build_message_json(self, conn, index, other_index):
        with self.lock:
            if self.clients[index].action == GET_ACTION:
                request = self.build_request(self.clients[index], self.clients[other_index])
            elif self.clients[index].action == DESTROY_ACTION:
                request = {
                    "action": DESTROY_ACTION,
                    "destroy_asteroid_id": self.clients[index].destroy_asteroid_id
                }
            else:
                request = self.build_request(self.clients[index], self.clients[other_index])
        
        # Send request
        try:
            # conn.sendall(json.dumps(request).encode('utf-8'))
            self.send_json(conn, request)

            self.clients[index].action = GET_ACTION
            self.clients[index].destroy_asteroid_id = None
        except (BrokenPipeError, ConnectionResetError) as e:
            raise BrokenPipeError()

    def handle_message_json(self, decoded, index, other_index):
        decoded_action = decoded.get("action")
        if decoded_action == DESTROY_ACTION:
            self.clients[other_index].action = DESTROY_ACTION
            self.clients[other_index].destroy_asteroid_id = decoded.get("destroy_asteroid_id")
        else:
            self.clients[index].update_data(decoded)
            # print(f"[#] Client {index+1} Position: {value}")

    def process_json(self, conn, index, other_index):
        self.build_message_json(conn, index, other_index)

        decoded = self.recv_json_message(conn)
        if decoded is None:
            raise OSError("[Server] Client disconnected.")
        with self.lock:
            self.handle_message_json(decoded, index, other_index)

    # PROCESS BYTES using TCP
    def build_action_message(self, index):
        action_data = struct.pack(ACTION_STRUCT, self.clients[index].action)
        msg = struct.pack(MSG_HEADER, len(action_data) + 1, MSG_TYPE_ACTION) + action_data
        return msg

    def build_client_message(self, index, other_index):
        client_data = struct.pack(CLIENT_STRUCT, self.clients[index].id, self.clients[other_index].is_connected)
        msg = struct.pack(MSG_HEADER, len(client_data) + 1, MSG_TYPE_CLIENT) + client_data
        return msg

    def build_player_message(self, other_index):
        player_data = struct.pack(PLAYER_STRUCT, self.clients[other_index].position[0], self.clients[other_index].position[1], self.clients[other_index].rotation)
        msg = struct.pack(MSG_HEADER, len(player_data) + 1, MSG_TYPE_PLAYER) + player_data
        return msg

    def build_asteroid_message(self, other_index):
        asteroid_data = b''
        for a in self.clients[other_index].asteroid_data:
            asteroid_data += struct.pack(ASTEROID_STRUCT, a["id"], a["x"], a["y"], a["radius"])
        msg = struct.pack(MSG_HEADER, len(asteroid_data) + 1, MSG_TYPE_ASTEROID) + asteroid_data
        return msg

    def build_shot_message(self, other_index):
        shot_data = b''
        for s in self.clients[other_index].shots_data:
            shot_data += struct.pack(SHOT_STRUCT, s["id"], s["x"], s["y"], s["radius"], s["used"])
        msg = struct.pack(MSG_HEADER, len(shot_data) + 1, MSG_TYPE_SHOT) + shot_data
        return msg

    def build_server_message(self):
        server_data = struct.pack(SERVER_DATA_STRUCT, self.num_connections)
        msg = struct.pack(MSG_HEADER, len(server_data) + 1, MSG_TYPE_SERVER_DATA) + server_data
        return msg

    def build_destroy_asteroid_message(self, index):
        destroy_asteroid_data = struct.pack(DESTROY_ASTEROID_STRUCT, self.clients[index].destroy_asteroid_id)
        msg = struct.pack(MSG_HEADER, len(destroy_asteroid_data) + 1, MSG_TYPE_DESTROY_ASTEROID) + destroy_asteroid_data
        return msg

    def send_game_state(self, sock, index, other_index):
        if self.clients[index].action == GET_ACTION:
            msg1 = self.build_action_message(index)
            msg2 = self.build_client_message(index, other_index)
            msg3 = self.build_player_message(other_index)
            msg5 = self.build_shot_message(other_index)
            msg6 = self.build_server_message()
            if self.clients[index].id == 2:
                msg4 = self.build_asteroid_message(other_index)
                sock.sendall(msg1 + msg2 + msg3 + msg4 + msg5 + msg6)  # Send all messages in one TCP packet
                # print(f"[Server] data to client: {msg1 + msg2 + msg3 + msg4 + msg5 + msg6}")
            else:
                sock.sendall(msg1 + msg2 + msg3 + msg5 + msg6)  # Send all messages in one TCP packet
                # print(f"[Server] data to client: {msg1 + msg2 + msg3 + msg5 + msg6}")
        elif self.clients[index].action == DESTROY_ACTION:
            msg7 = self.build_destroy_asteroid_message(index)
            sock.sendall(msg7)
            self.action = GET_ACTION
            self.destroy_asteroid_id = None
        else:
            print(f"[Server] invalid action: {self.clients[index].action}")

    def handle_message(self, msg_type, payload, index, other_index):
        if msg_type == MSG_TYPE_ACTION:
            self.clients[index].action = struct.unpack(ACTION_STRUCT, payload)[0]

        elif msg_type == MSG_TYPE_SERVER_DATA:
            self.num_connections = struct.unpack(SERVER_DATA_STRUCT, payload)[0]

        elif msg_type == MSG_TYPE_CLIENT:
            self.clients[index].id, self.clients[index].is_connected = struct.unpack(CLIENT_STRUCT, payload)

        elif msg_type == MSG_TYPE_PLAYER:
            position_x, position_y, self.clients[index].rotation = struct.unpack(PLAYER_STRUCT, payload)
            self.clients[index].position = (position_x, position_y)

        elif msg_type == MSG_TYPE_ASTEROID:
            size = struct.calcsize(ASTEROID_STRUCT)
            if self.clients[index].id == 1 and size > 0:
                self.clients[index].asteroid_data = []
                for i in range(0, len(payload), size):
                    id, x, y, radius = struct.unpack(ASTEROID_STRUCT, payload[i:i+size])
                    self.clients[index].asteroid_data.append({
                        "id": id, 
                        "x": x, 
                        "y": y, 
                        "radius": radius
                        })

        elif msg_type == MSG_TYPE_SHOT:
            size = struct.calcsize(SHOT_STRUCT)
            if size > 0:
                self.clients[index].shots_data = []
                for i in range(0, len(payload), size):
                    id, x, y, radius, used = struct.unpack(SHOT_STRUCT, payload[i:i+size])
                    self.clients[index].shots_data.append({
                        "id": id, 
                        "x": x, 
                        "y": y, 
                        "radius": radius, 
                        "used": used
                        })

        elif msg_type == MSG_TYPE_DESTROY_ASTEROID:
            self.clients[other_index].destroy_asteroid_id = struct.unpack(DESTROY_ASTEROID_STRUCT, payload)[0]
            self.clients[other_index].action = DESTROY_ACTION

        elif msg_type == MSG_TYPE_PING:
            self.clients[index].action = PING_ACTION

    def process_bytes(self, conn, index, other_index):
        buffer = b''
        self.send_game_state(conn, index, other_index)
        # can only get 4096 bytes at a time
        data = conn.recv(4096)
        if not data:
            # print("[Server] end of packet")
            return
        buffer += data
        while True:
            if len(buffer) < 5:
                # print(f"[Server] len(buffer) < 5")
                break  # wait for full header

            # B is char is message type (ie which object it is)
            msg_len, msg_type = struct.unpack('!IB', buffer[:5])
            total_len = 5 + (msg_len - 1)

            if len(buffer) < total_len:
                # print(f"[Server] buffer done")
                break  # wait for full payload

            payload = buffer[5:total_len]
            self.handle_message(msg_type, payload, index, other_index)
            buffer = buffer[total_len:]

    # UDP
    def start_server_udp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            self.server_socket = s
            s.settimeout(30.0)
            s.bind((self.host, self.port))
            print(f"[SERVER] Listening on {self.host}:{self.port}...")

            while True:
                for client in self.clients:
                    if client.last_seen is None:
                        continue
                    elif datetime.now().timestamp() - client.last_seen > 600: # if the client is inactive for 10 minutes
                        with self.lock:
                            client.reset_data()
                            self.num_connections -= 1
                            print(f"[Server] Client {client.id} disconnected")
                try:
                    data, addr = s.recvfrom(4096)
                    index = self.find_or_assign_slot_udp(addr)
                    if index is not None:
                        response = self.handle_udp_message(data, addr, index)
                        s.sendto(response, addr)
                except Exception as e:
                    print("[UDP Error]", e)

    def find_or_assign_slot_udp(self, addr):
        with self.lock:
            for i, client in enumerate(self.clients):
                if client.addr[i] == addr[0]:
                    self.clients[i].last_seen = datetime.now().timestamp()
                    return i
            for i, client in enumerate(self.clients):
                if client.addr[i] is None:
                    self.clients[i].addr = addr
                    self.num_connections += 1
                    print(f"[Server] num_connections: {self.num_connections}")
                    self.clients[i].last_seen = datetime.now().timestamp()
                    return i
        return None

    def handle_udp_message(self, data, addr, index):
        # print(f"[+] Client {index+1} connected: {addr}")
        try:
            other_index = 1 - index
            try:
                response = self.process_bytes_udp(data, addr, index, other_index)
                return response
            except OSError as e:
                print(e) # socket was closed
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"[!] Client {index+1} send error: {e}")
            except Exception as e:
                print(f"[!] Error receiving from Client {index+1}: {e}")
        finally:
                # print(f"[x] Client {index+1} cleanup done.")
                pass

    def send_game_state_udp(self, index, other_index):
        if self.clients[index].action == GET_ACTION:
            msg1 = self.build_action_message(index)
            msg2 = self.build_client_message(index, other_index)
            msg3 = self.build_player_message(other_index)
            msg5 = self.build_shot_message(other_index)
            msg6 = self.build_server_message()
            if self.clients[index].id == 2:
                msg4 = self.build_asteroid_message(other_index)
                return msg1 + msg2 + msg3 + msg4 + msg5 + msg6 
            else:
                return msg1 + msg2 + msg3 + msg5 + msg6
        elif self.clients[index].action == DESTROY_ACTION:
            msg = self.build_destroy_asteroid_message(index)
            self.action = GET_ACTION
            self.destroy_asteroid_id = None
            return msg
        elif self.clients[index].action == PING_ACTION:
            msg = self.build_ping_message()
            return msg
        else:
            print(f"[Server] invalid action: {self.clients[index].action}")

    def process_bytes_udp(self, data, addr, index, other_index):
        buffer = b''
        if not data:
            raise Exception("No data from client")
        buffer += data
        while True:
            if len(buffer) < 5:
                # print(f"[Server] len(buffer) < 5")
                break  # wait for full header

            # print(f"header payload: {buffer[:5]}")
            msg_len, msg_type = struct.unpack('!IB', buffer[:5])
            total_len = 5 + (msg_len - 1)

            if len(buffer) < total_len:
                # print(f"[Server] buffer done")
                break  # wait for full payload

            payload = buffer[5:total_len]
            self.handle_message(msg_type, payload, index, other_index)
            buffer = buffer[total_len:]
        # print(f"action: {self.clients[index].action}")
        return self.send_game_state_udp(index, other_index)

    def build_ping_message(self):
        ping_data = struct.pack(PING_STRUCT, True)
        msg = struct.pack(MSG_HEADER, len(ping_data) + 1, MSG_TYPE_PING) + ping_data
        return msg

    def disconnect_udp(self):
        self.server_socket.close()
        print("Server closed")

# HOST = '127.0.0.1'
# PORT = 65432

# def main():
#     server = Server(HOST, PORT)
#     server.start_server()

# if __name__ == "__main__":
#     main()