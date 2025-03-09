import time
import socket
import threading

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 4096

MAX_FAILURES = 3
CLEANUP_INTERVAL = 5
INACTIVITY_TIMEOUT = 30

client_failures = {}
client_timestamp = {}

server_sent_messages = 0

lock = threading.Lock()

# Function to increment client failure count and remove if exceeded
def increment_failure_count(client_address):
    client_failures[client_address] += 1
    if client_failures[client_address] >= MAX_FAILURES:
        remove_client_due_to_failures(client_address)

# Function to remove a client due to repeated failures
def remove_client_due_to_failures(client_address):
    del client_failures[client_address]
    del client_timestamp[client_address]
    print(f"Client {client_address} removed due to repeated failures.")

# Function to handle incoming messages and broadcast them
def handle_client(server_socket):
    global server_sent_messages
    while True:
        try:
            message, client_address = server_socket.recvfrom(BUFFER_SIZE)
            current_time = time.time()
            
            if len(message) < 2:
                print("Received an invalid message, ignoring...")
                increment_failure_count(client_address)
                continue

            # Extract username length
            username_length = message[0]

            if len(message) < 1 + username_length:
                print("Received a malformed message, ignoring...")
                increment_failure_count(client_address)
                continue
            
            try:
                username = message[1:1 + username_length].decode('utf-8')
            except UnicodeDecodeError:
                print("Error decoding username, ignoring this message.")
                increment_failure_count(client_address)
                continue

            try:
                message_body = message[1 + username_length:].decode('utf-8')
            except UnicodeDecodeError:
                print("Error decoding message body, ignoring this message.")
                increment_failure_count(client_address)
                continue

            # print(f"{username}: {message_body}")

            with lock:
                client_failures[client_address] = 0
                client_timestamp[client_address] = current_time

            # Broadcast the message to all clients
            for client in list(client_timestamp.keys()):
                try:
                    server_socket.sendto(message, client)
                    with lock:
                        server_sent_messages += 1
                except Exception as e:
                    increment_failure_count(client)

        except Exception as e:
            print(f"Error: {e}")


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


def print_server_statistics():
    while True:
        time.sleep(3)
        print(f"Total messages sent by server: {server_sent_messages}")


if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    print(f"Server started on {SERVER_HOST}:{SERVER_PORT}")
    
    # args must be a tuple, even if there is only one argument
    thread = threading.Thread(target=handle_client, args=(server_socket,))
    thread.start()

    cleanup_thread = threading.Thread(target=remove_inactive_clients, daemon=True)
    cleanup_thread.start()

    statistics_thread = threading.Thread(target=print_server_statistics, daemon=True)
    statistics_thread.start()
