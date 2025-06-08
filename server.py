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
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port}...")

            while True:
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

    def build_request(self, client, other_client):
        if client.id == 1:
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
                    conn.sendall(json.dumps(request).encode('utf-8'))
                    self.clients[index].action = GET_ACTION
                    self.clients[index].destroy_asteroid_id = None
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

# HOST = '127.0.0.1'
# PORT = 65432

# def main():
#     server = Server(HOST, PORT)
#     server.start_server()

# if __name__ == "__main__":
#     main()