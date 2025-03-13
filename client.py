import json
import socket
import threading


SERVER_HOST = "127.0.0.1"
UDP_PORT = 12345
TCP_PORT = 12346
BUFFER_SIZE = 4096

username = input("Enter your username: ")
room_name = input("Enter the chat room name: ")
operation = input("Create room (1) or Join room (2)? ")

tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.connect((SERVER_HOST, TCP_PORT))

room_name_bytes = room_name.encode('utf-8')
username_bytes = username.encode('utf-8')
room_name_size = len(room_name_bytes)


CREATE_ROOM = 1
JOIN_ROOM = 2

REQUEST = 0
ACKNOWLEDGE = 1
COMPLETE = 2

if operation == str(CREATE_ROOM):
    operation = CREATE_ROOM
elif operation == str(JOIN_ROOM):
    operation = JOIN_ROOM
else:
    print("Invalid option! Exiting...")
    tcp_socket.close()
    exit()

room_name_size = len(room_name_bytes)
payload_size = len(username_bytes)
header = bytes([room_name_size, operation, REQUEST]) + payload_size.to_bytes(29, 'big')
tcp_socket.send(header)

response = tcp_socket.recv(BUFFER_SIZE)
response_data = json.loads(response.decode('utf-8'))
if response_data.get("status") != ACKNOWLEDGE:
    tcp_socket.close()
    exit()

payload = room_name_bytes + username_bytes
tcp_socket.send(payload)

response = tcp_socket.recv(BUFFER_SIZE)
response_data = json.loads(response.decode('utf-8'))

if response_data.get("status") == COMPLETE:
    token = response_data["token"]
    print(f"Successfully joined {room_name}")
else:
    print(f"Failed to join room")
    tcp_socket.close()
    exit()

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind(("", 0))
udp_port = udp_socket.getsockname()[1]

udp_port_bytes = udp_port.to_bytes(2, 'big')
tcp_socket.send(udp_port_bytes)

tcp_socket.close()


def receive_messages():
    while True:
        try:
            message, _ = udp_socket.recvfrom(BUFFER_SIZE)
            print()
            print(message.decode('utf-8'))
            print()
        except Exception:
            pass


threading.Thread(target=receive_messages, daemon=True).start()

while True:
    try:
        message_body = input("Type message: ")
        if message_body.lower() == "/exit":
            print("Leaving chat...")
            break

        message_bytes = message_body.encode('utf-8')
        token_bytes = token.encode('utf-8')
        final_message = bytes([room_name_size, len(token_bytes)]) + room_name_bytes + token.encode('utf-8') + message_bytes
        udp_socket.sendto(final_message, (SERVER_HOST, UDP_PORT))
    except KeyboardInterrupt:
        print("\nExiting...")
        break

udp_socket.close()
