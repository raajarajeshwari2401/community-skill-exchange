"""
socket_client.py
-----------------
Companion to socket_server.py - the CLIENT side of the plain Python
socket demo (Socket Programming college requirement).

    1. Create a TCP socket.
    2. Connect to the server's (host, port).
    3. Send a message describing a skill exchange request.
    4. Receive and print the server's notification reply.

Run AFTER starting socket_server.py in another terminal:

    python socket_client.py
    python socket_client.py Alice Bob "Python Programming"
"""

import socket
import sys

HOST = "127.0.0.1"
PORT = 65432


def send_request(requester="Alice", provider="Bob", skill="Python Programming"):
    message = f"REQUEST:{requester}:{provider}:{skill}"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        print(f"[SOCKET CLIENT] Connected to {HOST}:{PORT}")
        print(f"[SOCKET CLIENT] Sending: {message}")
        client_socket.sendall(message.encode("utf-8"))

        response = client_socket.recv(1024)
        print(f"[SOCKET CLIENT] Server replied: {response.decode('utf-8')}")


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        send_request(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        send_request()
