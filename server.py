import socket
import threading
import time
import json

HOST = '127.0.0.1'
PORT = 65432
MAX_CONNECTIONS = 2
NUM_CONNECTIONS = 0

class Client_Data():
    def __init__(self):
        self.conn_addr = None  # (conn, addr)
        self.position = (0, 0)
        self.rotation = 0
        self.is_connected = False,
        self.asteroid_data = [],
        self.id = 0
        self.shots_data = []

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

def build_request(client, other_client):
    global NUM_CONNECTIONS
    if client.id == 1:
        # print(f"OTHER_ASTS: {other_client.asteroid_data}")
        return {
            "peer_data": {
            "action": "get_position", 
            "position": other_client.position, 
            "rotation": other_client.rotation, 
            "is_connected": other_client.is_connected,
            "shots_data": other_client.shots_data
            },
            "num_connections": NUM_CONNECTIONS,
            "asteroid_data": other_client.asteroid_data
        }
    else:
        return {
            "peer_data": {
            "action": "get_position", 
            "position": other_client.position, 
            "rotation": other_client.rotation, 
            "is_connected": other_client.is_connected,
            "shots_data": other_client.shots_data
            },
            "num_connections": NUM_CONNECTIONS
        }

# Shared state
clients = [Client_Data(), Client_Data()]
lock = threading.Lock()

def handle_client(conn, addr, index):
    global clients
    global NUM_CONNECTIONS
    print(f"[+] Client {index+1} connected: {addr}")
    try:
        while True:
            with lock:
                other_index = 1 - index
                request = build_request(clients[index], clients[other_index])
            
            # Send request
            try:
                conn.sendall(json.dumps(request).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"[!] Client {index+1} send error: {e}")
                break

            # Receive response
            try:
                data = conn.recv(8192)
                if not data:
                    print(f"[-] Client {index+1} disconnected")
                    break
                decoded = json.loads(data.decode('utf-8'))
                with lock:
                    clients[index].update_data(decoded)
                    # print(f"[#] Client {index+1} Position: {value}")
            except Exception as e:
                print(f"[!] Error receiving from Client {index+1}: {e}")
                break

            time.sleep(0.01)  # Reduce CPU usage
    finally:
        with lock:
            clients[index].reset_data()
            NUM_CONNECTIONS -= 1
            print(f"[x] Client {index+1} cleanup done.")
        conn.close()

def find_free_slot():
    with lock:
        for i in range(MAX_CONNECTIONS):
            if clients[i].conn_addr is None:
                global NUM_CONNECTIONS
                NUM_CONNECTIONS += 1
                return i
    return None

# Main server loop
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}...")

    while True:
        conn, addr = s.accept()
        slot = find_free_slot()
        if slot is None:
            print("[!] Connection refused: max clients reached")
            conn.close()
            continue
        with lock:
            clients[slot].conn_addr = (conn, addr)
        thread = threading.Thread(target=handle_client, args=(conn, addr, slot), daemon=True)
        thread.start()