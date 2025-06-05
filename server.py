import socket
import threading
import time
import json

HOST = '127.0.0.1'
PORT = 65432
MAX_CONNECTIONS = 2

# Shared state
clients = [None, None]  # (conn, addr)
all_data = [{"position": (0, 0), "rotation": 0}, {"position": (0, 0), "rotation": 0}] # {position: (x,y)}
lock = threading.Lock()

def handle_client(conn, addr, index):
    global clients, all_data
    print(f"[+] Client {index+1} connected: {addr}")
    try:
        while True:
            with lock:
                other_index = 1 - index
                position_value = all_data[other_index]["position"]
                rotation_value = all_data[other_index]["rotation"]
                request = {"action": "get_position", "position": position_value, "rotation": rotation_value}
            
            # Send request
            try:
                conn.sendall(json.dumps(request).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"[!] Client {index+1} send error: {e}")
                break

            # Receive response
            try:
                data = conn.recv(1024)
                if not data:
                    print(f"[-] Client {index+1} disconnected")
                    break
                decoded = json.loads(data.decode('utf-8'))
                position = decoded["position"]
                rotation = decoded["rotation"]
                with lock:
                    all_data[index] = {"position": position, "rotation": rotation}
                    # print(f"[#] Client {index+1} Position: {value}")
            except Exception as e:
                print(f"[!] Error receiving from Client {index+1}: {e}")
                break

            time.sleep(0.01)  # Reduce CPU usage
    finally:
        with lock:
            clients[index] = None
            all_data[index] = {"position": (0, 0), "rotation": 0}
            print(f"[x] Client {index+1} cleanup done.")
        conn.close()

def find_free_slot():
    with lock:
        for i in range(MAX_CONNECTIONS):
            if clients[i] is None:
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
            clients[slot] = (conn, addr)
        thread = threading.Thread(target=handle_client, args=(conn, addr, slot), daemon=True)
        thread.start()