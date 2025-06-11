import struct
import socket
import threading
import time
import json

from constants import *

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

    def update_data(self, decoded_json):
        self.position = decoded_json.get("position")
        self.rotation = decoded_json.get("rotation")
        self.is_connected = decoded_json.get("is_connected")
        self.asteroid_data = decoded_json.get("asteroid_data")
        self.id = decoded_json.get("id")
        self.shots_data = decoded_json.get("shots_data")

    def reset_data(self):
        self.conn_addr = None
        self.position = (0,0)
        self.rotation = 0
        self.is_connected = False
        self.asteroid_data = []
        self.id = 0
        shots_data = []

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
        print("Local IP address:", self.get_local_ip())
        print("Local IP address (filtered):", self.get_local_ip_filtered())
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
                with self.lock:
                    other_index = 1 - index

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
                    print(f"[!] Client {index+1} send error: {e}")
                    break

                # Receive response
                try:
                    # data = conn.recv(8192)
                    # if not data:
                    #     print(f"[-] Client {index+1} disconnected")
                    #     break
                    # decoded = json.loads(data.decode('utf-8'))

                    decoded = self.recv_json_message(conn)
                    if decoded is None:
                        print("[Server] Client disconnected.")
                        break

                    decoded_action = decoded.get("action")
                    if decoded_action == DESTROY_ACTION:
                        self.clients[other_index].action = DESTROY_ACTION
                        self.clients[other_index].destroy_asteroid_id = decoded.get("destroy_asteroid_id")
                    else:
                        with self.lock:
                            self.clients[index].update_data(decoded)
                        # print(f"[#] Client {index+1} Position: {value}")
                except Exception as e:
                    print(f"[!] Error receiving from Client {index+1}: {e}")
                    break

                time.sleep(0.01)  # Reduce CPU usage
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

    # PROCESS JSON
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

    # PROCESS BYTES
    def handle_message(self, msg_type, payload, index, other_index):
        if msg_type == MSG_TYPE_ACTION:
            action = struct.unpack(ACTION_STRUCT, payload[i:i+size])
            if action == DESTROY_ACTION:
                    self.clients[other_index].action = DESTROY_ACTION
                    self.clients[other_index].destroy_asteroid_id = decoded.get("destroy_asteroid_id") # need to build this on client
            else:
                with self.lock:
                    pass
                    # need to make update on Client class to handle byte data
                    # self.clients[index].update_data(decoded)

        elif msg_type == MSG_TYPE_SERVER_DATA:
            self.num_connections = struct.unpack(SERVER_DATA_STRUCT, payload)

        elif msg_type == MSG_TYPE_CLIENT:
            size = struct.calcsize(CLIENT_STRUCT)
            for i in range(0, len(payload), size):
                self.client_id, self.is_peer_connected = struct.unpack(CLIENT_STRUCT, payload[i:i+size])
                # can probably optimize this to not use a loop, we know it is always one item

        elif msg_type == MSG_TYPE_PLAYER:
            size = struct.calcsize(PlAYER_STRUCT)
            for i in range(0, len(payload), size):
                self.peer_position.x, self.peer_position.y, self.peer_rotation = struct.unpack(PlAYER_STRUCT, payload[i:i+size])
                # can probably optimize this to not use a loop, we know it is always one item

        elif msg_type == MSG_TYPE_ASTEROID:
            size = struct.calcsize(ASTEROID_STRUCT)
            for i in range(0, len(payload), size):
                id, x, y, radius = struct.unpack(ASTEROID_STRUCT, payload[i:i+size])
                self.asteroids.append(Asteroid_Peer(pygame.Vector2(x, y),radius,id))

        elif msg_type == MSG_TYPE_SHOT:
            size = struct.calcsize(SHOT_STRUCT)
            for i in range(0, len(payload), size):
                id, x, y, radius, used = struct.unpack(SHOT_STRUCT, payload[i:i+size])
                self.peer_shots.append(Shot_Peer(x,y,radius,id,used))


    def process_bytes(self, index, other_index):
        buffer = b''
        while True:
            # can only get 4096 bytes at a time
            data = self.client_socket.recv(4096)
            if not data:
                break
            buffer += data
            while True:
                if len(buffer) < 5:
                    break  # wait for full header

                # B is char is message type (ie which object it is)
                msg_len, msg_type = struct.unpack('!IB', buffer[:5])
                total_len = 5 + (msg_len - 1)

                if len(buffer) < total_len:
                    break  # wait for full payload

                payload = buffer[5:total_len]
                self.handle_message(msg_type, payload)
                buffer = buffer[total_len:]
                    
            # self.send_game_state()

# HOST = '127.0.0.1'
# PORT = 65432

# def main():
#     server = Server(HOST, PORT)
#     server.start_server()

# if __name__ == "__main__":
#     main()