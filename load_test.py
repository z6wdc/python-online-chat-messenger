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

lock = threading.Lock()

sending = True
received_message_count = 0

def receive_messages(client_socket):
    global received_message_count
    while sending:
        try:
            client_socket.recvfrom(BUFFER_SIZE)
            with lock:
                received_message_count += 1
        except Exception:
            break


def send_messages(client_socket):
    username_bytes = USERNAME.encode('utf-8')
    username_length = len(username_bytes)
    message_bytes = MESSAGE.encode('utf-8')
    final_message = bytes([username_length]) + username_bytes + message_bytes

    for _ in range(MESSAGES_PER_THREAD):
        client_socket.sendto(final_message, (SERVER_HOST, SERVER_PORT))


def run_load_test():
    global sending

    sockets = []    
    threads = []
    for _ in range(NUM_THREADS):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(2)
        sockets.append(client_socket)

        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,), name="receive")
        receive_thread.start()
        threads.append(receive_thread)

    time.sleep(0.5)

    start_time = time.time()
    for client_socket in sockets:
        send_thread = threading.Thread(target=send_messages, args=(client_socket, ), name="send")
        send_thread.start()
        threads.append(send_thread)

    for thread in threads:
        if thread.name == "send":
            thread.join()
        
    end_time = time.time()

    time.sleep(0.5)
    sending = False

    for thread in threads:
        if thread.name == "receive":
            thread.join()

    total_messages = NUM_THREADS * MESSAGES_PER_THREAD
    elapsed_time = end_time - start_time
    print(f"Sent {total_messages} messages in {elapsed_time:.2f} seconds")
    print(f"Throughput: {total_messages / elapsed_time:.2f} messages per second")
    print(f"Received {received_message_count} messages back from the server.")

    for client_socket in sockets:
        try:
            client_socket.close()
        except Exception as e:
            print(f"Error closing socket: {e}")

if __name__ == "__main__":
    run_load_test()
