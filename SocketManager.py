from message import *
import socket
import select
import json
import time
import threading
import rsa
import os
from base64 import b64encode, b64decode

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

        if self.mediator.get_my_username() is not None:
            self.mediator.put_udp_action(MessageID.ONLINE, None, None, BROADCAST_IP)

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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        sock.setblocking(False)
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
                    inputs + waiting + list(self.peer_sockets.keys()), 1)
                for sock in readable:
                    if sock is tcp_socket:     # new chat, someone binded successfully
                        conn, addr = tcp_socket.accept()
                        waiting.append(conn)
                        print(f"Someone new connected from: {addr}")
                    elif sock in self.peer_sockets:
                        data = sock.recv(4096)
                        if data:
                            private_key = self.mediator.get_my_private_key(sock.getpeername())
                            decrypted_data = rsa.decrypt(data, private_key).decode()
                            message_dict = json.loads(decrypted_data)
                            message = Message(**message_dict)
                            if message.messageID == MessageID.PERSONAL:
                                print(f"Received a personal message: {message_dict}")
                                self.mediator.put_ui_action(Actions.PEER_MESSAGE, message.senderGUID, message.senderUsername, sock.getpeername(), message.message)
                        else:
                            print("Someone from peers is disconnecting")
                            self.mediator.remove_connected_peer(self.peer_sockets[sock])
                            self.mediator.remove_online_peer(self.peer_sockets[sock])
                            del self.peer_sockets[sock]
                            sock.close()
                    elif sock in waiting:
                        data = sock.recv(4096)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = Message(**message_dict)
                            if message.messageID == MessageID.INIT:
                                print("Received init message")
                                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                                self.peer_sockets[sock] = message.senderGUID
                                self.mediator.add_connected_peer(message.senderGUID)
                                self.mediator.update_peer_public(message.senderGUID, self.string_to_public_rsa(message.message))
                                message_to_send = self.mediator.get_waiting_message(message.senderGUID)
                                if message_to_send is not None:
                                    self.mediator.put_tcp_action(Actions.MY_MESSAGE, message.senderGUID, message.senderUsername, MessageID.PERSONAL, message_to_send) 
                                waiting.remove(sock) 
                        else:
                            print("Someone from waiting is disconnecting")
                            self.mediator.remove_online_peer(self.peer_sockets[sock])
                            waiting.remove(sock)
                            sock.close()                     
                for sock in exceptional:
                    print("Exceptional socket")
                    if sock in self.peer_sockets:
                        self.mediator.remove_online_peer(self.peer_sockets[sock])
                        self.mediator.remove_connected_peer(self.peer_sockets[sock])
                        del self.peer_sockets[sock]
                        sock.close()

            except socket.error as socket_error:
                print(F"Socket error: {socket_error}")
                if sock in self.peer_sockets:
                    self.mediator.remove_connected_peer(self.peer_sockets[sock])
                    self.mediator.remove_online_peer(self.peer_sockets[sock])
                    del self.peer_sockets[sock]
                    sock.close()
            except Exception as e:
                print(f"Error receiving TCP: {e}")
                
    def send_tcp(self):    
        while True:
            result = self.mediator.get_tcp_action()
            if result is not None:
                message_id, peer_guid, peer_username, message_content = result
                sock = list(self.peer_sockets.keys())[list(self.peer_sockets.values()).index(peer_guid)]
                message = Message(message_id, str(self.mediator.get_my_guid()), self.mediator.get_my_username(), message_content)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                print(f"Sending TCP message: {message_dict}")
                try:
                    if message_id == MessageID.INIT:
                        sock.sendall(message_json.encode())
                    else:
                        sock.sendall(rsa.encrypt(message_json.encode(), self.mediator.get_peer_public_key(peer_guid)))
                        self.mediator.put_ui_action(Actions.MY_MESSAGE, peer_guid, peer_username, sock.getpeername(), message_content)
                except Exception as e:
                    print(f"Error sending TCP: {e}")
            time.sleep(0.1)
    
    def recv_udp(self, udp_socket):
        while True:
            try:
                data, addr = udp_socket.recvfrom(3072)

                if addr[0] != socket.gethostbyname(socket.gethostname()):
                    message_dict = json.loads(data.decode())
                    message = Message(**message_dict)
                    print(f"Received broadcast from {addr}: {message_dict}")
                    if message.messageID == MessageID.ONLINE:
                        print(f"{message.senderUsername} is online")
                        self.mediator.add_online_peer(message.senderGUID, message.senderUsername, addr)
                        if message.message is None:
                            self.mediator.put_udp_action(MessageID.ONLINE, message.senderGUID, "ACK", addr[0])
                    elif message.messageID == MessageID.OFFLINE:
                        self.mediator.remove_online_peer(message.senderGUID)
                        self.mediator.remove_connected_peer(message.senderGUID)
                    elif message.messageID == MessageID.START: # someone wants to start TCP, connect to them using TCP socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                        try:
                            sock.connect((addr[0], TCP_PORT))
                            self.peer_sockets[sock] = message.senderGUID
                            self.mediator.add_connected_peer(message.senderGUID)
                            self.mediator.add_online_peer(message.senderGUID, message.senderUsername, sock.getpeername())
                            public_key = self.mediator.generate_keys(message.senderGUID)
                            self.mediator.update_peer_public(message.senderGUID, self.string_to_public_rsa(message.message))
                            self.mediator.put_tcp_action(Actions.INIT, message.senderGUID, message.senderUsername, MessageID.INIT, self.public_rsa_to_string(public_key)) 
                        except Exception as e:
                            print(f"Error connection to peer: {e}")
            except Exception as e:
                print(f"Error receiving UDP: {e}")
                
    def send_udp(self, udp_socket):
        while True:
            result = self.mediator.get_udp_action()
            if result is not None:
                message_id, to_send_guid, message, ip_addr = result
                if message_id == MessageID.START:
                    public_key = self.mediator.generate_keys(to_send_guid)
                    message_content = self.public_rsa_to_string(public_key)
                else:
                    message_content = message

                message = Message(message_id, str(self.mediator.get_my_guid()), self.mediator.get_my_username(), message_content)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)

                try:
                    udp_socket.sendto(message_json.encode(), (ip_addr, UDP_PORT))
                    if message.messageID == MessageID.OFFLINE:
                        self.disconnect_tcp_sockets()
                        time.sleep(2)
                        os._exit(1)
                except Exception as e:
                    print(f"Error sending UDP: {e}")
            time.sleep(0.2)

    def disconnect_tcp_sockets(self):
        for sock in self.peer_sockets.keys():
            sock.close() 
        self.peer_sockets.clear()

    def string_to_public_rsa(self, key_str):
        return rsa.PublicKey.load_pkcs1(b64decode(key_str.encode()))
    
    def public_rsa_to_string(self, key):
        return b64encode(key.save_pkcs1("PEM")).decode()
