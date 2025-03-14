import json
import socket
import textwrap
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


def print_message_box(message):
    wrapped_message = textwrap.fill(message, width=40)
    border = "+" + "-" * 42 + "+"
    print(border)
    for line in wrapped_message.split("\n"):
        print(f"| {line.ljust(40)} |")
    print(border)


def receive_messages():
    while True:
        try:
            message, _ = udp_socket.recvfrom(BUFFER_SIZE)
            decoded_message = message.decode('utf-8')

            if "Chatroom" in decoded_message and "has been closed." in decoded_message:
                print_message_box(decoded_message)
                udp_socket.close()
                exit()

            print_message_box(decoded_message)
        except Exception:
            pass


threading.Thread(target=receive_messages, daemon=True).start()

while True:
    try:
        message_body = input()
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
