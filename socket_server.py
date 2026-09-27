"""
socket_server.py
----------------
College requirement demonstrated: SOCKET PROGRAMMING (Client-Server),
using Python's built-in `socket` module directly - separate from the
Flask-SocketIO layer used inside the web app for browser notifications.

This is a deliberately small, plain TCP server so it is easy to explain
line-by-line in a viva:

    1. Create a TCP socket.
    2. Bind it to (host, port).
    3. Listen for incoming connections.
    4. Accept a connection -> get a client socket.
    5. Receive bytes, decode to text.
    6. Print/print a simple "notification" and send a reply back.
    7. Close the connection.

Run this file in one terminal, then run socket_client.py in another
terminal to see the exchange happen.

    Terminal 1:  python socket_server.py
    Terminal 2:  python socket_client.py
"""

import socket

HOST = "127.0.0.1"
PORT = 65432


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[SOCKET SERVER] Listening on {HOST}:{PORT} ... (Ctrl+C to stop)")

        while True:
            conn, addr = server_socket.accept()
            with conn:
                print(f"[SOCKET SERVER] Connected by {addr}")
                data = conn.recv(1024)
                if not data:
                    continue

                message = data.decode("utf-8")
                print(f"[SOCKET SERVER] Received: {message}")

                # Simulate the same kind of notification the web app sends,
                # e.g. "REQUEST:Alice:Bob:Python Programming"
                parts = message.split(":")
                if len(parts) >= 4 and parts[0] == "REQUEST":
                    _, requester, provider, skill = parts[0], parts[1], parts[2], parts[3]
                    notification = (
                        f"New Skill Exchange Request received: "
                        f"{requester} wants to learn '{skill}' from {provider}."
                    )
                else:
                    notification = f"Notification: {message}"

                print(f"[SOCKET SERVER] -> {notification}")
                conn.sendall(notification.encode("utf-8"))


if __name__ == "__main__":
    start_server()
