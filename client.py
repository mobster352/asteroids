import socket
import json

class Client():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.position = None
        self.rotation = 0
        self.peer_data = None
        self.run = True,
        self.num_connections = 0

    def connect(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            while self.run:
                try:
                    request = s.recv(1024)
                    if not request:
                        print("[Client] Server disconnected.")
                        break
                    decoded = json.loads(request.decode('utf-8'))
                    # print(f"[Client] Server says: {decoded}")
                    self.peer_data = decoded.get("peer_data")
                    self.num_connections = decoded.get("num_connections")

                    action = self.peer_data.get("action")
                    if action == "get_position":
                        data = {
                            "position": self.position, 
                            "rotation": self.rotation, 
                            "is_connected": True
                            }
                        s.sendall(json.dumps(data).encode('utf-8'))
                except Exception as e:
                    print(f"[Client] Error: {e}")
                    break

    def update_position(self, position):
        self.position = (position.x, position.y)

    def update_rotation(self, rotation):
        self.rotation = rotation

    def kill_client(self):
        self.run = False