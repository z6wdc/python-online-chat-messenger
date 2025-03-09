import time
import socket
import threading

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345
BUFFER_SIZE = 4096
NUM_THREADS = 100
MESSAGES_PER_THREAD = 100
USERNAME = "test_user"
MESSAGE = "This is a significantly longer test message to better simulate real-world chat conditions and enhance load testing. It ensures that message handling and network performance can be effectively evaluated under realistic conditions."


def send_messages():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    username_bytes = USERNAME.encode('utf-8')
    username_length = len(username_bytes)
    message_bytes = MESSAGE.encode('utf-8')
    final_message = bytes([username_length]) + username_bytes + message_bytes

    for _ in range(MESSAGES_PER_THREAD):
        client_socket.sendto(final_message, (SERVER_HOST, SERVER_PORT))
    
    client_socket.close()


def run_load_test():
    start_time = time.time()
    
    threads = []
    for _ in range(NUM_THREADS):
        thread = threading.Thread(target=send_messages)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
    
    end_time = time.time()
    total_messages = NUM_THREADS * MESSAGES_PER_THREAD
    elapsed_time = end_time - start_time
    print(f"Sent {total_messages} messages in {elapsed_time:.2f} seconds")
    print(f"Throughput: {total_messages / elapsed_time:.2f} messages per second")

if __name__ == "__main__":
    run_load_test()
