import uuid
import time
import socket
import threading

SERVER_HOST = '127.0.0.1'
UDP_PORT = 12345
TCP_PORT = 12346

BUFFER_SIZE = 4096

MAX_FAILURES = 3
CLEANUP_INTERVAL = 10
INACTIVITY_TIMEOUT = 300
MAX_ROOM_NAME_SIZE = 256

chat_rooms = {}
active_tokens = {}

client_failures = {}
client_timestamp = {}

lock = threading.Lock()

# Operation Codes
CREATE_ROOM = 1
JOIN_ROOM = 2

# State Codes
REQUEST = 0
ACKNOWLEDGE = 1
COMPLETE = 2

def generate_token():
    return str(uuid.uuid4())


def receive_full_data(client_socket, expected_size):
    receive_data = b''
    while len(receive_data) < expected_size:
        chunk = client_socket.recv(min(BUFFER_SIZE, expected_size - len(receive_data)))
        if not chunk:
            break
        receive_data += chunk

    return receive_data


def handle_tcp_client(cleint_socket, client_address):
    try:
        header = client_socket.recv(32)
        if not header and len(header) < 32:
            return
        
        # analyze header
        room_name_size = header[0]
        operation = header[1]
        state = header[2]
        payload_size = int.from_bytes(header[3:32], 'big')

        # validate
        if room_name_size <= 0 or room_name_size > MAX_ROOM_NAME_SIZE:
            return
        if operation not in (CREATE_ROOM, JOIN_ROOM):
            return
        if state not in (REQUEST, ACKNOWLEDGE, COMPLETE):
            return

        payload = receive_full_data(client_socket, payload_size).decode('utf-8')
        if len(payload) < payload_size:
            return

        room_name = payload[:room_name_size]
        username = payload[room_name_size:]

        with lock:
            if operation == CREATE_ROOM and state == REQUEST:
                acknowledge_response = json.dumps({"status": ACKNOWLEDGE}).encode('utf-8')
                client_socket.send(acknowledge_response)

                if room_name in chat_rooms:
                    response = json.dumps({"error": "Room name already exists"}).encode('utf-8')
                    client_socket.send(response)
                else:
                    token = generate_token()
                    chat_rooms[room_name] = {"host_token": token, "host_address": client_address, "members": {}}
                    active_tokens[token] = (room_name, client_address, username)
                    
                    completion_response = json.dumps({"status": COMPLETE, "token": token}).encode('utf-8')
                    client_socket.send(completion_response)

            elif operation == JOIN_ROOM and state == REQUEST:
                token = generate_token()
                if room_name in chat_rooms:
                    chat_rooms[room_name]["members"][token] = (client_address, username)
                    active_tokens[token] = (room_name, client_address, username)
                    response = json.dumps({"status": STATE_COMPLETE, "token": token}).encode('utf-8')
                    client_socket.send(response)
                else:
                    response = json.dumps({"error": "Room not found"}).encode('utf-8')
                    client_socket.send(response)
    finally:
        client_socket.close()


def handle_udp_messages(server_socket):
    while True:
        message, client_address = server_socket.recvfrom(BUFFER_SIZE)

        if len(message) < 2:
            print(f"Invalid message from {client_address}: Too short")
            continue

        room_name_size = message[0]
        token_size = message[1]
        
        if room_name_size <= 0 or token_size <= 0:
            print(f"Invalid message from {client_address}: Invalid sizes")
            continue

        expected_min_size = 2 + room_name_size + token_size
        if len(message) < expected_min_size:
            print(f"Invalid message from {client_address}: Incomplete data")
            continue

        try:
            room_name = message[2:2 + room_name_size].decode('utf-8')
        except UnicodeDecodeError:
            print(f"Invalid UTF-8 encoding in room name from {client_address}")
            continue

        try:
            token = message[2 + room_name_size:2 + room_name_size + token_size].decode('utf-8')
        except UnicodeDecodeError:
            print(f"Invalid UTF-8 encoding in ㄙㄜ from {client_address}")
            continue
        
        with lock:
            if token in active_tokens and active_tokens[token][0] == room_name:
                client_timestamp[client_address] = time.time()
                client_failures[client_address] = 0
                
                sender_username = active_tokens.get(token, (None, None, "Unknown"))[2]
                relay_message = sender_username.encode('utf-8') + b':' + message[2 + room_name_size + token_size:]

                for member_token, (address, _) in chat_rooms[room_name]["members"].items():
                    if address != client_address:
                        server_socket.sendto(relay_message, address)
                
                host_address = chat_rooms[room_name]["host_address"]
                if host_address != client_address:
                    server_socket.sendto(relay_message, host_address)


# increment client failure count and remove if exceeded
def increment_failure_count(client_address):
    client_failures[client_address] += 1
    if client_failures[client_address] >= MAX_FAILURES:
        del client_failures[client_address]
        del client_timestamp[client_address]
        print(f"Client {client_address} removed due to repeated failures.")


def remove_inactive_clients():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        current_time = time.time()
        with lock:
            for client in list(client_timestamp.keys()):
                if current_time - client_timestamp[client] > INACTIVITY_TIMEOUT:
                    del client_failures[client]
                    del client_timestamp[client]
                    print(f"Client {client} removed due to inactivity.")


def start_tcp_server():
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind((SERVER_HOST, TCP_PORT))
    tcp_server.listen(5)
    print(f"TCP server started on {SERVER_HOST}:{TCP_PORT}")
    
    while True:
        client_socket, client_address = tcp_server.accept()
        threading.Thread(target=handle_tcp_client, args=(client_socket, client_address)).start()


def start_udp_server():
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server.bind((SERVER_HOST, UDP_PORT))
    print(f"UDP server started on {SERVER_HOST}:{UDP_PORT}")
    
    handle_udp_messages(udp_server)


if __name__ == "__main__":
    threading.Thread(target=start_tcp_server, daemon=True).start()
    threading.Thread(target=start_udp_server, daemon=True).start()
    threading.Thread(target=remove_inactive_clients, daemon=True).start()
    
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Shutting down server...")
