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

        self.mediator.put_udp_action(BROADCAST_IP, MessageID.ONLINE, None)

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
                        waiting.append(conn)
                        print(f"Someone new connected from: {addr}")
                        # TODO update peers info - address and username if needed, only if already present in db
                    elif sock in self.peer_sockets:
                        data = sock.recv(2048)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = Message(**message_dict)
                            if (message.messageID is MessageID.PERSONAL):
                                print(f"Received a personal message: {message_dict}")
                                self.mediator.put_ui_action(Actions.PEER_MESSAGE, message.senderGUID, message.senderUsername, sock.getsockname(), message.message)
                        else:
                            print("Someone is disconnecting")
                            self.mediator.remove_online_peer(self.peer_sockets[sock])
                            self.mediator.remove_connected_peer(self.peer_sockets[sock])
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
                                self.mediator.add_connected_peer(message.senderGUID)
                                print("added to peer_sockets")
                                message_to_send = self.mediator.get_waiting_message(message.senderGUID)
                                print(f"Got waiting message: {message_to_send}")
                                if message_to_send is not None:
                                    self.mediator.put_tcp_action(Actions.MY_MESSAGE, message.senderGUID, MessageID.PERSONAL, message_to_send)
                                    self.mediator.put_ui_action(Actions.MY_MESSAGE, message.senderGUID, message.senderUsername, sock.getsockname(), message_to_send)
                for sock in exceptional:
                    self.mediator.remove_online_peer(self.peer_sockets[sock])
                    self.mediator.remove_connected_peer(self.peer_sockets[sock])
                    del self.peer_sockets[sock] 
            except Exception as e:
                print("SOMETHING IS BAD")
                print(e)
                
    def send_tcp(self):    
        while True:
            result = self.mediator.get_tcp_action()
            if result is not None:
                socket = list(self.peer_sockets.keys())[list(self.peer_sockets.values()).index(result[1])]
                message = Message(result[0], str(self.mediator.get_my_guid()), "vickyko", result[2])
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                try:
                    socket.sendall(message_json.encode())
                except Exception as e:
                    print(f"Exception when sending TCP: {e}")
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
                            self.mediator.put_udp_action(message.senderGUID, MessageID.ONLINE, "ACK")
                    elif message.messageID == MessageID.OFFLINE:
                        self.mediator.remove_online_peer(message.senderGUID)
                    elif message.messageID == MessageID.START: # someone wants to start TCP, connect to them using TCP socket
                        print("Received START message")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            sock.connect((addr[0], int(message.message)))
                            self.peer_sockets[sock] = message.senderGUID
                            self.mediator.put_tcp_action(Actions.INIT, message.senderGUID, MessageID.INIT, None)
                        except Exception as e:
                            print(f"Exception connection to peer: {e}")
                    else:
                        print("im in else")
            except Exception as e:
                print(e)
                
    def send_udp(self, udp_socket):
        while True:
            result = self.mediator.get_udp_action()
            if result is not None:
                if result[1] == MessageID.OFFLINE:
                    self.disconnect_tcp_sockets()

                if result[1] == MessageID.START:
                    message_content = TCP_PORT
                else:
                    message_content = result[2] 
                       
                message = Message(result[1], str(self.mediator.get_my_guid()), "vickyko", message_content)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                udp_socket.sendto(message_json.encode(), (result[0], UDP_PORT))
            time.sleep(0.2)

    def disconnect_tcp_sockets(self):
        for sock in self.peer_sockets.keys():
            sock.close()