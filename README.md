# Online Chat Messenger

This is a simple UDP-based chat messenger that allows multiple clients to communicate with each other via a central server.

## Features
- Clients can connect to the server via a CLI interface.
- Messages are relayed to all connected clients.
- The maximum message size is 4096 bytes.
- Supports usernames with a maximum length of 255 bytes.
- Encodes and decodes messages in UTF-8.

## Installation
### Prerequisites
- Python 3.6 or later

## Running the Server
```sh
python3 server.py
```

## Running the Client
```sh
python3 client.py
```

## Usage
1. Start the server first.
2. Run multiple clients and enter usernames when prompted.
3. Type messages to communicate with other connected clients.
4. Type `exit` to leave the chat.
