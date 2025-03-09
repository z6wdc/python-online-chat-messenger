import socket
import threading

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 4096

# Function to receive messages from the server
def receive_messages(client_socket):
    while True:
        try:
            message, _ = client_socket.recvfrom(BUFFER_SIZE)

            if len(message) < 2:
                print("Received an invalid message, ignoring...")
                continue
            
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
        except Exception as e:
            print(f"Error occurred: {e}, continuing to receive messages...")

# Start UDP Client
def start_client():
    while True:
        username = input("Enter your username: ")
        username_bytes = username.encode('utf-8')
        username_length = len(username_bytes)
    
        if username_length > 255:
            print("Username is too long! Maximum 255 bytes allowed. Please enter a shorter username.")
        else:
            break
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Start a thread to listen for messages
    # args must be a tuple, even if there is only one argument
    # Set daemon=True so the thread exits when the main program ends
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
    receive_thread.start()
    
    print("You can start typing messages. Type 'exit' to quit.")
    while True:
        message_body = input()
        if message_body.lower() == 'exit':
            print("Exiting chat...")
            break

        message_bytes = message_body.encode('utf-8')
        total_size = 1 + username_length + len(message_bytes)
        if total_size > BUFFER_SIZE:
            print(f"Message too long! Maximum {BUFFER_SIZE - 1 - username_length} bytes allowed.")
            continue

        final_message = bytes([username_length]) + username_bytes + message_bytes
        client_socket.sendto(final_message, (SERVER_HOST, SERVER_PORT))

if __name__ == "__main__":
    start_client()
