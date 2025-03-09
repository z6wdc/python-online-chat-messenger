import json
import socket
import threading

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 4096

clients = set()

# Function to handle incoming messages and broadcast them
def handle_client(server_socket):
    while True:
        try:
            message, client_address = server_socket.recvfrom(BUFFER_SIZE)
            
            if len(message) < 2:
                print("Received an invalid message, ignoring...")
                continue

            # Extract username length
            username_length = message[0]

            if len(message) < 1 + username_length:
                print("Received a malformed message, ignoring...")
                continue
            
            try:
                username = message[1:1 + username_length].decode('utf-8')
            except UnicodeDecodeError:
                print("Error decoding username, ignoring this message.")
                continue

            try:
                message_body = message[1 + username_length:].decode('utf-8')
            except UnicodeDecodeError:
                print("Error decoding message body, ignoring this message.")
                continue

            print(f"{username}: {message_body}")
            
            # Store the client address
            clients.add(client_address)
            
            # Broadcast the message to all clients
            for client in clients:
                server_socket.sendto(message, client)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    print(f"Server started on {SERVER_HOST}:{SERVER_PORT}")
    
    # args must be a tuple, even if there is only one argument
    thread = threading.Thread(target=handle_client, args=(server_socket,))
    thread.start()