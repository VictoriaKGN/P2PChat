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
    online_peers = {} # dict guid: [addr, username] 
    peers_info = [] # list of (Guid, Username, Address, LastChat)
    waiting_messages = {} # dict guid: message
    connected_peers = [] # list of guids
    
    db_lock = threading.Lock()

    curr_index = None

    def __init__(self):
        self.TCP_out_queue = queue.Queue()
        self.TCP_in_queue = queue.Queue()
        self.UDP_out_queue = queue.Queue()

        self.db_manager = DBManager()
        self.init_guid()
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
        print(f"Online Peers: {self.online_peers}")

    def remove_online_peer(self, guid):
        del self.online_peers[guid]
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
        
    def receive_message(self, is_me, sender_guid, sender_username, address, message):
        self.TCP_in_queue.put((is_me, sender_guid, sender_username, address, message))
        
    def get_receive_message(self):
        if self.TCP_in_queue.qsize() > 0:
            # TODO update chat history
            popped = self.TCP_in_queue.get(block=False)

            if popped[0] is not True:
                self.write_to_db(popped[1], popped[1], popped[4])

            if self.curr_index is None:
                if popped[0] is True:
                    self.curr_index = 0
                else:
                    self.curr_index = None
                updated = self.db_manager.update_peer_info(str(popped[1]), popped[2], f"{popped[3][0]}:{str(popped[3][1])}", datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                        print(f"Peers info: {self.peers_info}")
            else:
                curr_guid = self.peers_info[self.curr_index][1]
                updated = self.db_manager.update_peer_info(str(popped[1]), popped[2], popped[3], datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                        if curr_guid is self.peers_info[1][0]: # incoming message from selected peer
                            self.curr_index = 0
                        else: # incoming message from non-selected peer
                            self.curr_index += 1
                    else:
                        # TODO deal with it
                        pass
                else:
                    # TODO deal with it
                    pass
            return (popped[1], self.curr_index)
        else:
            return None
        
    def send_message(self, guid, message, is_first, username=None, addr=None, message_id=MessageID.PERSONAL):
        print(f"Checking if {guid} is online: {guid in self.online_peers}")
        if guid in self.online_peers:
            self.write_to_db(guid, str(self.my_guid), message) # TODO check if its init
            self.curr_index = 0

            if is_first is not True:
                updated = self.db_manager.update_peer_lastchat(guid, datetime.now())
            else:
                updated = self.db_manager.update_peer_info(guid, username, f"{addr[0]}:{str(addr[1])}", datetime.now())

            if updated is True:
                fetched = self.db_manager.fetch_peers_info()
                if fetched is not False:
                    self.peers_info = fetched
                    print(self.peers_info)
            self.TCP_out_queue.put((guid, message_id, message))

        if not message_id == MessageID.INIT:
            self.TCP_out_queue.put((guid, message_id, message))

    def get_send_message(self):
        if self.TCP_out_queue.qsize() > 0: 
            return self.TCP_out_queue.get(block=False)
        else:
            return None
        
    def put_ui_action(self, action_type, peer_guid, peer_username, peer_address, message_content):
        self.TCP_in_queue.put((action_type, peer_guid, peer_username, peer_address, message_content))
    
    def get_ui_action(self):
        if self.TCP_in_queue.qsize() > 0:
            popped = self.TCP_in_queue.get(block=False) # popped = (action_type, peer_guid, peer_username, peer_address, message_content)
            action_type, peer_guid, peer_username, peer_address, message_content = popped

            if action_type == Actions.MY_MESSAGE:
                self.write_to_db(peer_guid, str(self.my_guid), message_content)
                updated = self.db_manager.update_peer_info(peer_guid, peer_username, f"{peer_address[0]}:{str(peer_address[1])}", datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                    else:
                        pass # TODO deal with it
                else:
                    pass # TODO deal with it
                self.curr_index = 0
            elif action_type == Actions.PEER_MESSAGE:
                curr_guid = self.peers_info[self.curr_index][1]
                self.write_to_db(peer_guid, peer_guid, message_content)
                updated = self.db_manager.update_peer_info(peer_guid, peer_username, f"{peer_address[0]}:{str(peer_address[1])}", datetime.now())
                if updated is True:
                    fetched = self.db_manager.fetch_peers_info()
                    if fetched is not False:
                        self.peers_info = fetched
                    else:
                        pass # TODO deal with it
                else:
                    pass # TODO deal with it
                
                if curr_guid is self.peers_info[1][0]:
                    self.curr_index = 0
                else:
                    if self.curr_index is not None: 
                        self.curr_index += 1
            return (action_type, peer_guid, peer_username, self.curr_index)
        else:
            return None

    def put_tcp_actions(self, action_type, peer_guid, message_id, message_content):
        self.TCP_out_queue.put((message_id, peer_guid, message_content))

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

    def init_guid(self):
        guid = self.db_manager.fetch_guid()

        if guid is False:
            pass # TODO there was an error, deal with it
        elif guid is not None:
            self.my_guid = uuid.UUID(guid)
        else:
            new_guid = uuid.uuid4()
            result = self.db_manager.init_guid(str(new_guid))
            if result is True:
                self.my_guid = new_guid
            else:
                # TODO deal with this
                pass
    
    def write_to_db(self, table_name, sender_id, message):
        result = self.db_manager.write_peer_message(table_name, sender_id, message)
        if result is not True:
            pass # TODO do something
    


    
    
        
   
    # def send_message(self, direct_queue):
    #     index = self.friends_listbox.curselection()[0]
    #     guid = self.friends_listbox.itemcget(index, "value")
    #     print(guid)
        
    # TODO base case of empty list
    def update_recent_list(self):
        index = self.friends_listbox.curselection()
        selected_guid = self.recent_chats[index]
        self.friends_listbox.delete("1.0", tkinter.END)
        
        for username in self.recent_chats:
            self.friends_listbox.insert(tkinter.END, username)
        index = self.recent_chats.index(selected_guid)
        
        self.friends_listbox.select_set(index)
        self.switch_chat_history(self.recent_chats[index])
        
    def fetch_history(self):
        # TODO fetch all rows of the table
        pass

    def close_window(self):
        self.put_udp_action("255.255.255.255", MessageID.OFFLINE, None)
        # broadcast_queue.put((BROADCAST_IP, MessageID.OFFLINE, None))
        time.sleep(2)
        os._exit(1)


peer = Peer()