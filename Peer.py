from message import *
from DBManager import DBManager
from UIManager import UIManager
from SocketManager import SocketManager
import socket
import threading
import tkinter
import json
import queue
import os
import time
import select
import sys
import uuid
from datetime import datetime

TCP_PORT = 8002
UDP_PORT = 8001
BROADCAST_IP = "255.255.255.255"

class Peer:
    my_guid = None
    my_username = None
    online_peers = {} # dict guid: [addr, username] 
    peers_info = [] # list of (Guid, Username, Address, LastChat)
    waiting_messages = {} # dict guid: message
    connected_peers = [] # list of guids
    curr_index = None
    
    db_lock = threading.Lock()

    def __init__(self):
        self.TCP_out_queue = queue.Queue()
        self.UI_queue = queue.Queue()
        self.UDP_out_queue = queue.Queue()

        self.db_manager = DBManager()
        self.init_app_info()
        self.init_peers_info()

        gui_thread = UIManager(self)
        gui_thread.start()
        
        self.socket_manager = SocketManager(self)
        
    def set_curr_index(self, new_index):
        self.curr_index = new_index

    def get_curr_index(self):
        return self.curr_index
    
    def get_peers_info(self):
        return self.peers_info
    
    def get_my_guid(self):
        return self.my_guid
    
    def get_my_username(self):
        return self.my_username
    
    def get_peer_history(self, peer_guid):
        table = self.db_manager.fetch_peer_table(str(peer_guid))
        return table

    def is_online(self, guid):
        return guid in self.online_peers

    def get_index_guid(self, index):
        return self.peers_info[index][0]
    
    def get_online_list(self):
        return list(self.online_peers.keys())

    def get_online_addr(self, guid):
        return self.online_peers[guid]
    
    def add_online_peer(self, guid, username, addr):
        self.online_peers[guid] = [addr, username]
        self.put_ui_action(Actions.OFFLINE, guid, None, None, None)
        print(f"Online Peers: {self.online_peers}")

    def get_online_username(self, guid):
        return self.online_peers[guid][1]

    def remove_online_peer(self, guid):
        del self.online_peers[guid]
        self.put_ui_action(Actions.OFFLINE, guid, None, None, None)
        print(f"Online Peers: {self.online_peers}")

    def get_waiting_message(self, guid):
        message = self.waiting_messages[guid]
        del self.waiting_messages[guid]
        return message
    
    def add_connected_peer(self, guid):
        self.connected_peers.append(guid)

    def remove_connected_peer(self, guid):
        self.connected_peers.remove(guid)

    def is_peer_connected(self, guid):
        return guid in self.connected_peers

    ########################### Shared Queues Functions ###########################
        
    def put_ui_action(self, action_type, peer_guid, peer_username, peer_address, message_content):
        self.UI_queue.put((action_type, peer_guid, peer_username, peer_address, message_content))
    
    def get_ui_action(self):
        if self.UI_queue.qsize() > 0:
            popped = self.UI_queue.get(block=False) # popped = (action_type, peer_guid, peer_username, peer_address, message_content)
            action_type, peer_guid, peer_username, peer_address, message_content = popped

            if action_type == Actions.MY_MESSAGE:
                self.write_to_db(peer_guid, str(self.my_guid), message_content)
                updated = self.db_manager.update_peer_info(peer_guid, peer_username, f"{peer_address[0]}:{str(peer_address[1])}", datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                    else:
                        print("Couldnt fetch peers info table") # TODO deal with it
                else:
                    print("Did not update peers info") # TODO deal with it
                self.curr_index = 0
            elif action_type == Actions.PEER_MESSAGE:
                if self.curr_index is not None:
                    curr_guid = self.peers_info[self.curr_index][0]
                else: 
                    curr_guid = None

                self.write_to_db(peer_guid, peer_guid, message_content)
                updated = self.db_manager.update_peer_info(peer_guid, peer_username, f"{peer_address[0]}:{str(peer_address[1])}", datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                    else:
                        print("Couldnt fetch peers info table")
                else:
                    print("Did not update peers info")
                
                if curr_guid == self.peers_info[0][0]:
                    print("Im first guid")
                    self.curr_index = 0
                else:
                    if self.curr_index is not None: 
                        self.curr_index += 1

            return (action_type, peer_guid, peer_username, self.curr_index)
        else:
            return None

    def put_tcp_action(self, action_type, peer_guid, peer_username, message_id, message_content):
        self.TCP_out_queue.put((message_id, peer_guid, peer_username, message_content))

    def get_tcp_action(self):
        if self.TCP_out_queue.qsize() > 0:
            return self.TCP_out_queue.get(block=False)
        else:
            return None
        
    def put_udp_action(self, to_send_guid, message_id, message):
        if to_send_guid == "255.255.255.255":
            self.UDP_out_queue.put((to_send_guid, message_id, message))
        else:
            if message_id == MessageID.START:
                self.waiting_messages[to_send_guid] = message
                self.UDP_out_queue.put((self.online_peers[to_send_guid][0][0], message_id, None))
            else:
                self.UDP_out_queue.put((self.online_peers[to_send_guid][0][0], message_id, message))

    def get_udp_action(self):
        if self.UDP_out_queue.qsize() > 0:
            return self.UDP_out_queue.get(block=False)
        else:
            return None
        
    ########################### Init Variables Functions ###########################
        
    def init_peers_info(self):
        peers_info = self.db_manager.fetch_peers_info()
        if peers_info is not False:
            self.peers_info = peers_info
        else:
            pass # TODO deal with it 

    def init_app_info(self):
        result = self.db_manager.fetch_app_info()

        if result is False:
            pass # TODO there was an error, deal with it
        elif result is not None:
            guid, username = result
            self.my_guid = uuid.UUID(guid)
            self.my_username = username
        else:
            new_guid = uuid.uuid4()
            result = self.db_manager.init_guid(str(new_guid))
            if result is True:
                self.my_guid = new_guid
                self.put_ui_action(Actions.USERNAME, None, None, None, None)
            else:
                # TODO deal with this
                pass

    def update_username(self, username):
        result = self.db_manager.update_username(username)
        if result is True:
            self.my_username = username
        else:
            pass # TODO deal with it
    
    def write_to_db(self, table_name, sender_id, message):
        result = self.db_manager.write_peer_message(table_name, sender_id, message)
        if result is not True:
            pass # TODO do something

    def close_window(self):
        self.put_udp_action("255.255.255.255", MessageID.OFFLINE, None)
        time.sleep(0.5)
        os._exit(1)


peer = Peer()
