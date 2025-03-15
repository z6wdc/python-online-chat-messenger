import json
import uuid
import time
import socket
import threading
from pprint import pprint

SERVER_HOST = '127.0.0.1'
UDP_PORT = 12345
TCP_PORT = 12346

BUFFER_SIZE = 4096

MAX_FAILURES = 3
CLEANUP_INTERVAL = 10
INACTIVITY_TIMEOUT = 60
MAX_ROOM_NAME_SIZE = 256

chat_rooms = {}
active_tokens = {}

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


def handle_tcp_client(client_socket, client_address):
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

        with lock:
            if operation == CREATE_ROOM and state == REQUEST:
                acknowledge_response = json.dumps({"status": ACKNOWLEDGE}).encode('utf-8')
                client_socket.send(acknowledge_response)

                payload = receive_full_data(client_socket, room_name_size + payload_size)
                if len(payload) < payload_size:
                    return

                room_name = payload[:room_name_size].decode('utf-8')
                username = payload[room_name_size:].decode('utf-8')

                if room_name in chat_rooms:
                    response = json.dumps({"error": "Room name already exists"}).encode('utf-8')
                    client_socket.send(response)
                else:
                    token = generate_token()
                    active_tokens[token] = (room_name, client_address, username)
                    chat_rooms[room_name] = {"host_token": token, "host_address": client_address, "members": {}}
                    
                    completion_response = json.dumps({"status": COMPLETE, "token": token}).encode('utf-8')
                    client_socket.send(completion_response)

                    udp_port_bytes = client_socket.recv(2)
                    if not udp_port_bytes:
                        print("Client did not send UDP port, closing connection.")
                        return
                        
                    udp_port = int.from_bytes(udp_port_bytes, 'big')
                    active_tokens[token] = (room_name, (client_address[0], udp_port), username)
                    chat_rooms[room_name] = {"host_token": token, "host_address": (client_address[0], udp_port), "members": {}}
                    client_timestamp[(client_address[0], udp_port)] = time.time()

            elif operation == JOIN_ROOM and state == REQUEST:
                acknowledge_response = json.dumps({"status": ACKNOWLEDGE}).encode('utf-8')
                client_socket.send(acknowledge_response)

                payload = receive_full_data(client_socket, room_name_size + payload_size).decode('utf-8')
                if len(payload) < payload_size:
                    return

                room_name = payload[:room_name_size]
                username = payload[room_name_size:]

                token = generate_token()

                if room_name in chat_rooms:
                    active_tokens[token] = (room_name, client_address, username)
                    chat_rooms[room_name]["members"][token] = (client_address, username)
                    response = json.dumps({"status": COMPLETE, "token": token}).encode('utf-8')
                    client_socket.send(response)

                    udp_port_bytes = client_socket.recv(2)
                    if not udp_port_bytes:
                        print("Client did not send UDP port, closing connection.")
                        return
                        
                    udp_port = int.from_bytes(udp_port_bytes, 'big')
                    active_tokens[token] = (room_name, (client_address[0], udp_port), username)
                    chat_rooms[room_name]["members"][token] = ((client_address[0], udp_port), username)
                    client_timestamp[(client_address[0], udp_port)] = time.time()

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
            print(f"Invalid UTF-8 encoding in from {client_address}")
            continue
        
        print("\nhandle_udp_messages")
        with lock:
            pprint(active_tokens)
            if token in active_tokens and active_tokens[token][0] == room_name:
                client_timestamp[client_address] = time.time()
                
                sender_username = active_tokens.get(token, (None, None, "Unknown"))[2]
                relay_message = sender_username.encode('utf-8') + b':' + message[2 + room_name_size + token_size:]
                
                print(room_name)
                print(client_address)
                print(relay_message)
                pprint(chat_rooms)

                for _, (address, _) in chat_rooms[room_name]["members"].items():
                    if address != client_address:
                        server_socket.sendto(relay_message, address)
                
                host_address = chat_rooms[room_name]["host_address"]
                if host_address != client_address:
                    server_socket.sendto(relay_message, host_address)
        
        print("handle_udp_messages\n")


def remove_inactive_clients(server_socket):
    print("\nremove_inactive_clients")
    while True:
        time.sleep(CLEANUP_INTERVAL)
        current_time = time.time()
        with lock:
            pprint(chat_rooms.items())
            for room_name, room_data in list(chat_rooms.items()):
                host_address = room_data["host_address"]

                # check each host in the chatroom
                if current_time - client_timestamp.get(host_address, 0) > INACTIVITY_TIMEOUT:
                    print(f"Host of room '{room_name}' disconnected. Closing room.")

                    close_message = f"Chatroom '{room_name}' has been closed.".encode('utf-8')
                    for member_token, (member_address, _) in room_data["members"].items():
                        server_socket.sendto(close_message, member_address)
                    
                    server_socket.sendto(close_message, room_data["host_address"])

                    for member_token in list(room_data["members"].keys()):
                        del active_tokens[member_token]
                        
                    del active_tokens[room_data["host_token"]]
                    del chat_rooms[room_name]
                    continue

                inactive_members = []
                # check each member in the chatroom
                for member_token, (member_address, _) in list(room_data["members"].items()):
                    last_active = client_timestamp.get(member_address, 0)
                    if current_time - last_active > INACTIVITY_TIMEOUT:
                        inactive_members.append((member_token, member_address))

                for member_token, member_address in inactive_members:
                    print(f"Removing inactive client {member_address} from {room_name}")
                    
                    remove_message = f"You have been removed from '{room_name}' due to inactivity.".encode('utf-8')
                    server_socket.sendto(remove_message, member_address)

                    del room_data["members"][member_token]
                    del active_tokens[member_token]
                    del client_timestamp[member_address]


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
    
    threading.Thread(target=remove_inactive_clients, args=(udp_server,), daemon=True).start()
    handle_udp_messages(udp_server)


if __name__ == "__main__":
    threading.Thread(target=start_tcp_server, daemon=True).start()
    threading.Thread(target=start_udp_server, daemon=True).start()
    
    try:
        while True:
            pass  # Keep the main thread alive
    except KeyboardInterrupt:
        print("\nShutting down server...")
