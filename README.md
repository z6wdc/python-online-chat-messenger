# Online Chat Messenger

A lightweight chatroom system that allows clients to create and join chatrooms using TCP for room management and UDP for real-time messaging.

## Features
- Create & Join Chatrooms.
- Reliable Room Management (TCP).
- Real-time Chat (UDP).

## Installation
### Prerequisites
- Python 3.8 or later

## Usage
### Running the Server
```sh
python3 server.py
```

### Running the Client
```sh
python3 client.py
```

Then follow the prompts:

```
Enter your username: AAA
Enter the chat room name: room
Create room (1) or Join room (2)? 0
Successfully joined room
```

### Sending Messages
Simply type a message and press Enter to send.

To exit the chatroom, type:
```
/exit
```