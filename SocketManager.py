import socket
import select
from message import *
import json
import time
import threading
import queue

TCP_PORT = 8002
UDP_PORT = 8001
BROADCAST_IP = "255.255.255.255"

# TODO open threads for every message handling, queue too
class SocketManager:
    def __init__(self, mediator):
        self.mediator = mediator
        udp_socket = self.open_udp()
        tcp_socket = self.open_tcp()
        
        broadcast_queue.put((BROADCAST_IP, MessageID.ONLINE, None))
        
        tcplistener_thread = threading.Thread(target=self.recv_tcp, args=(tcp_socket, peer_sockets))
        tcplistener_thread.start()
        
        tcpsender_thread = threading.Thread(target=self.send_tcp, args=(direct_queue, ))
        tcpsender_thread.start()

        udplistener_thread = threading.Thread(target=self.recv_udp, args=(udp_socket, broadcast_queue))
        udplistener_thread.start()
        
        udpsender_thread = threading.Thread(target=self.send_udp, args=(udp_socket, broadcast_queue))
        udpsender_thread.start()

    def open_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_PORT))
        return sock
    
    def open_tcp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", TCP_PORT))
        sock.listen()
        return sock
    
    def recv_tcp(self, tcp_socket, peer_sockets):
        inputs = [tcp_socket, ]
        waiting = []
        outputs = []
        
        while True:
            try:
                readable, writable, exceptional = select.select(
                    inputs + waiting + list(peer_sockets.keys()),
                    outputs,
                    inputs + waiting + list(peer_sockets.keys()))
                
                for sock in readable:
                    if sock is tcp_socket:     # new chat, someone binded successfully
                        conn, addr = tcp_socket.accept()
                        waiting.append(conn)
                    elif sock in self.peer_sockets:
                        data = sock.recv(2048)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = TCPMessage(**message_dict)
                            # self.write_to_db(str(message.senderID), str(message.senderID), message.message)
                            # TODO change GUI
                            # TODO update peers info table
                            # TODO check message ID
                            self.mediator.receive_message(message.senderID, message.message)
                    elif sock in waiting:
                        data = sock.recv(2048)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = TCPMessage(**message_dict)
                            if message.messageID is MessageID.INIT:
                                waiting.remove(sock)
                                peer_sockets[sock] = message.senderID
            except Exception as e:
                print("SOMETHING IS BAD")
                print(e)
                
    def send_tcp(self, direct_queue):    
        while True:
            if direct_queue.qsize() > 0:
                socket, messageID, message = direct_queue.get(block=False)
                message = TCPMessage(messageID, self.my_guid, message)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)

                try:
                    socket.sendall(message_json.encode())
                except Exception:
                    pass
            time.sleep(500)
    
    def recv_udp(self, udp_socket, broadcast_queue, direct_queue):
        while True:
            try:
                data, addr = udp_socket.recvfrom(2048)
                
                if addr[0] != socket.gethostbyname(socket.gethostname()):
                    print(f"Received broadcast from {addr}: {data.decode()}")
                    message_dict = json.loads(data.decode())
                    message = UDPMessage(**message_dict)
                    if message.messageID is MessageID.ONLINE:
                        self.online_peers.append(message.senderID)
                        if not message.message:
                            broadcast_queue.put((addr[0], MessageID.ONLINE, "ACK"))
                    elif message.messageID is MessageID.OFFLINE:
                        self.online_peers.remove(message.senderID)
                    elif message.messageID is MessageID.START: # someone wants to start TCP, connect to them using TCP socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((addr[0], message.message)) # TODO conver to int
                        self.peer_sockets[sock] = message.senderID
                        direct_queue.put((sock, MessageID.INIT, None))
            except Exception as e:
                print(e)
                
    def send_udp(self, udp_socket, broadcast_queue):
        while True:
            if broadcast_queue.qsize() > 0:
                addrIP, messageID, message = broadcast_queue.get(block=False)
                message = UDPMessage(messageID, self.my_guid, "vickyko", message)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                udp_socket.sendto(message_json.encode(), (addrIP, UDP_PORT))
            time.sleep(500)