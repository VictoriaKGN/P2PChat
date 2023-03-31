from message import *
import socket
import select
import json
import time
import threading

TCP_PORT = 8002
UDP_PORT = 8001
BROADCAST_IP = "255.255.255.255"

# TODO open threads for every message handling, queue too
class SocketManager:
    peer_sockets = {} # dict socket: guid

    def __init__(self, mediator):
        self.mediator = mediator
        udp_socket = self.open_udp()
        tcp_socket = self.open_tcp()

        udplistener_thread = threading.Thread(target=self.recv_udp, args=(udp_socket, ))
        udplistener_thread.start()

        self.mediator.send_broadcast(BROADCAST_IP, MessageID.ONLINE, None)

        udpsender_thread = threading.Thread(target=self.send_udp, args=(udp_socket, ))
        udpsender_thread.start()
        
        tcplistener_thread = threading.Thread(target=self.recv_tcp, args=(tcp_socket, ))
        tcplistener_thread.start()
        
        tcpsender_thread = threading.Thread(target=self.send_tcp)
        tcpsender_thread.start()


    def open_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_PORT))
        return sock
    
    def open_tcp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", TCP_PORT))
        sock.listen()
        return sock
    
    def recv_tcp(self, tcp_socket):
        inputs = [tcp_socket, ]
        waiting = []
        outputs = []
        
        while True:
            try:
                readable, writable, exceptional = select.select(
                    inputs + waiting + list(self.peer_sockets.keys()),
                    outputs,
                    inputs + waiting + list(self.peer_sockets.keys()))
                
                for sock in readable:
                    if sock is tcp_socket:     # new chat, someone binded successfully
                        conn, addr = tcp_socket.accept()
                        conn.settimeout()
                        waiting.append(conn)
                        print(f"Someone new connected from: {addr}")
                        # TODO update peers info - address and username if needed, only if already present in db
                    elif sock in self.peer_sockets:
                        data = sock.recv(2048)
                        if data:
                            print("Received a personal message")
                            message_dict = json.loads(data.decode())
                            message = Message(**message_dict)
                            if (message.messageID is MessageID.PERSONAL):
                                print(message)
                                self.mediator.receive_message(message.senderGUID, message.senderUsername, sock.getsockname(), message.message)
                        else:
                            self.mediator.remove_online_peer(self.peer_sockets[sock])
                            del self.peer_sockets[sock]
                    elif sock in waiting:
                        data = sock.recv(2048)
                        if data:
                            print("Received init message")
                            message_dict = json.loads(data.decode())
                            message = Message(**message_dict)
                            if message.messageID == MessageID.INIT:
                                print("Im in init")
                                waiting.remove(sock)
                                print("Removed from waiting")
                                self.peer_sockets[sock] = message.senderGUID
                                print("added to peer_sockets")
                                message_to_send = self.mediator.get_waiting_message(message.senderGUID)
                                print(f"Got waiting message: {message_to_send}")
                                if message_to_send is not None:
                                    self.mediator.send_message(message.senderGUID, message_to_send, True, message.senderUsername, sock.getsockname())
                                    self.mediator.receive_message(True, message.senderGUID, message.senderUsername, sock.getsockname(), "")
                for sock in exceptional:
                    self.mediator.remove_online_peer(self.peer_sockets[sock])
                    del self.peer_sockets[sock] 
            except Exception as e:
                print("SOMETHING IS BAD")
                print(e)
                
    def send_tcp(self):    
        while True:
            result = self.mediator.get_send_message()
            if result is not None:
                socket = {i for i in self.peer_sockets if self.peer_sockets[i] == result[0]}
                message = Message(result[1], str(self.mediator.get_my_guid()), "vickyko", result[2])
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                try:
                    socket.sendall(message_json.encode())
                except Exception:
                    pass
            time.sleep(0.2)
    
    def recv_udp(self, udp_socket):
        while True:
            try:
                data, addr = udp_socket.recvfrom(2048)
                print(f"Received broadcast from {addr}: {data.decode()}")

                if addr[0] != socket.gethostbyname(socket.gethostname()):
                    message_dict = json.loads(data.decode())
                    message = Message(**message_dict)
                    # print(f"Message type: {message.messageID}")
                    if message.messageID == MessageID.ONLINE:
                        print(f"{message.senderUsername} is online")
                        self.mediator.add_online_peer(message.senderGUID, message.senderUsername, addr)
                        if not message.message:
                            self.mediator.send_broadcast(message.senderGUID, MessageID.ONLINE, "ACK")
                    elif message.messageID == MessageID.OFFLINE:
                        self.mediator.remove_online_peer(message.senderGUID)
                    elif message.messageID == MessageID.START: # someone wants to start TCP, connect to them using TCP socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((addr[0], message.message)) # TODO conver to int
                        self.peer_sockets[sock] = message.senderGUID
                        self.mediator.send_message()
                        # direct_queue.put((sock, MessageID.INIT, None)) TODO
                    else:
                        print("im in else")
            except Exception as e:
                print(e)
                
    def send_udp(self, udp_socket):
        while True:
            result = self.mediator.get_send_broadcast()
            if result is not None:
                if result[1] == MessageID.START:
                    message_content = TCP_PORT
                else:
                    message_content = result[2]    
                message = Message(result[1], str(self.mediator.get_my_guid()), "vickyko", message_content)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                udp_socket.sendto(message_json.encode(), (result[0], UDP_PORT))
            time.sleep(0.2)