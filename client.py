import socket
import threading
import tkinter
import sqlite3
from message import *
import json
import queue
import os
import time
import select
import sys
import uuid

TCP_PORT = 8002
UDP_PORT = 8001
BROADCAST_IP = "255.255.255.255"

class Client:
    my_guid = None
    # chat_histories = {
    #     "Friend 1": ["Hi", "How are you?", "I'm fine, thanks."],
    #     "Friend 2": ["Hey", "What's up?", "Not much, just chilling."],
    #     "Friend 3": ["Yo", "Sup?", "Nm, hbu?"]}
    online = {} # peer guid: username
    my_friends = {} # peer socket: guid
    recent_chats = [] # list of guids as they appear in left panel
    db_lock = threading.Lock()

    def __init__(self):
        self.init_guid()
        # udp_socket = self.open_udp()
        # tcp_socket = self.open_tcp()
        broadcast_queue = queue.Queue()
        direct_queue = queue.Queue()

        # tcplistener_thread = threading.Thread(target=self.recv_tcp)
        # tcplistener_thread.starT()

        # udplistener_thread = threading.Thread(target=self.recv_udp, args=(udp_socket, broadcast_queue))
        # udplistener_thread.start()

        # broadcast_queue.put((BROADCAST_IP, MessageID.ONLINE, None))

        # udpsender_thread = threading.Thread(target=self.send_udp, args=(udp_socket, broadcast_queue))
        # udpsender_thread.start()

        gui_thread = threading.Thread(target=self.gui_loop, args=(broadcast_queue, direct_queue))
        gui_thread.start()
        
    def init_recents(self):
        conn = sqlite3.connect('chat_info.db')
        
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS Recents (senderID TEXT)")
            conn.commit()
            # TODO grab all rows and save into self.recent_chats
            
            
        except Exception as e:
            print(e)

    def init_guid(self):
        conn = sqlite3.connect('chat_info.db')

        try:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AppGuid'").fetchone()

            if not result:
                conn.execute("CREATE TABLE AppGuid (Guid TEXT)")
                conn.commit() 
                self.my_guid = uuid.uuid4()
                conn.execute("INSERT INTO AppGuid (Guid) VALUES (?)", (str(self.my_guid), ))
                conn.commit()                
            else:
                guid = conn.execute("SELECT Guid FROM AppGuid").fetchone()[0]
                self.my_guid = uuid.UUID(guid)
        except Exception as e:
            print(e)
        finally:
            conn.close()

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
    
    def write_to_db(self, table_name, senderID, message):
        try:
            self.db_lock.acquire()
            conn = sqlite3.connect('chat_info.db')
            conn.execute(f"INSERT INTO {table_name} VALUES (?, ?)", (senderID, message))
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.db_lock.release()
    
    def recv_tcp(self, tcp_socket):
        inputs = [tcp_socket, ]
        waiting = []
        outputs = []
        
        while True:
            try:
                readable, writable, exceptional = select.select(
                    inputs + waiting + list(self.my_friends.keys()),
                    outputs,
                    inputs + waiting + list(self.my_friends.keys()))
                
                for sock in readable:
                    if sock is tcp_socket:     # new chat, someone binded successfully
                        conn, addr = tcp_socket.accept()
                        waiting.append(conn)
                    elif sock in self.my_friends:
                        data = sock.recv(2048)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = TCPMessage(**message_dict)
                            self.write_to_db(str(message.senderID), str(message.senderID), message.message)
                            # change GUI
                    elif sock in waiting:
                        data = sock.recv(2048)
                        if data:
                            message_dict = json.loads(data.decode())
                            message = TCPMessage(**message_dict)
                            if message.messageID is MessageID.INIT:
                                waiting.remove(sock)
                                self.my_friends[sock] = message.senderID
                                self.init_db(message.senderID)

            except Exception as e:
                print("SOMETHING IS BAD")
                print(e)
                sys.exit(0)  

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
                        self.online[message.senderID] = message.senderUsername
                        if not message.message:
                            broadcast_queue.put((addr[0], MessageID.ONLINE, "ACK"))
                    elif message.messageID is MessageID.OFFLINE:
                        del self.online[message.senderID]
                    elif message.messageID is MessageID.START: # someone wants to start TCP, connect to them using TCP socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((addr[0], message.message)) # TODO conver to int
                        self.my_friends[sock] = message.senderID
                        self.init_db(message.senderID)
                        direct_queue.put((sock, MessageID.INIT, None))
                    print(self.online)
            except Exception as e:
                print(e)

    def init_db(self, table_name):
        conn = sqlite3.connect('chat_info.db')

        try:
            conn.execute("CREATE TABLE IF NOT EXISTS {table_name} (senderID TEXT, message TEXT)")
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()
    
    def send_udp(self, udp_socket, broadcast_queue):
        while True:
            if broadcast_queue.qsize() > 0:
                addrIP, messageID, message = broadcast_queue.get(block=False)
                message = UDPMessage(messageID, self.my_guid, "vickyko", message)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                udp_socket.sendto(message_json.encode(), (addrIP, UDP_PORT))
            time.sleep(500)
        
    def gui_loop(self, broadcast_queue, direct_queue):
        width = 1200
        height = 750
        self.win = tkinter.Tk()
        self.win.geometry(f"{width}x{height}")
        self.win.resizable(False, False)
        self.win.title("Definitely Not Discord")
        tkinter.Widget

        left_frame = tkinter.Frame(self.win, width=int(width/4), height=height, bg="#2C2D31")
        left_frame.pack(side="left")

        # options_frame = tkinter.Frame(left_frame, width=20, height=20, bg="#2C2D31")
        # options_frame.pack(side="top")

        # username_text = tkinter.Text(options_frame, width=20, height=1)
        # username_text.pack(side="left", padx=10, pady=10)
        # username_text.insert(tkinter.END, "User")

        newchat_button = tkinter.Button(left_frame, text="New Chat", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF")
        newchat_button.pack(side="top", padx=10, pady=10)

        self.friends_listbox = tkinter.Listbox(left_frame, bg="#2C2D31", fg="#FFFFFF", width=30, height=50, borderwidth=0, highlightthickness=0, font=12, selectbackground="#414249", activestyle="none", exportselection=False)
        self.friends_listbox.pack(side="bottom", padx=10, pady=10)
        self.friends_listbox.bind('<<ListboxSelect>>', lambda event=None: self.switch_chat_history(self.recent_chats[self.friends_listbox.curselection()]))

        # for friend_name in self.chat_histories.keys():
        #     self.friends_listbox.insert(tkinter.END, friend_name)
        self.update_recent_list()

        right_frame = tkinter.Frame(self.win, width=int(3*width/4), height=750, bg="#323338")
        right_frame.pack(side="right")

        name_frame = tkinter.Frame(right_frame, width=20, height=40, bg="#323338")
        name_frame.pack(side="top", pady=5)

        circle_canvas = tkinter.Canvas(name_frame, width=15, height=15, bg="#323338", borderwidth=0, highlightthickness=0)
        circle_canvas.pack(side="left", padx=2, pady=2)
        circle_canvas.create_oval(2, 2, 15, 15, fill="Green")

        self.friendname_label = tkinter.Label(name_frame, text="", bg="#323338", fg="#FFFFFF", font=12)
        self.friendname_label.pack(side="right", padx=2, pady=2)

        self.chathistory_text = tkinter.Text(right_frame, width=int(3*width/4), height=41, bg="#323338", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        self.chathistory_text.pack(side="top", padx=10, pady=4)
        
        input_frame = tkinter.Frame(right_frame, bg="#323338", width=int(3*width/4), height=50)
        input_frame.pack(side="bottom", padx=10, pady=10)
        
        self.input_text = tkinter.Text(input_frame, width=100, height=1, bg="#414249", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        self.input_text.pack(side="left")
        
        sendinput_button = tkinter.Button(input_frame, text="Send", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF", command= lambda: self.send_message(direct_queue))
        sendinput_button.pack(side="right")

        self.friends_listbox.select_set(0)
        self.switch_chat_history(self.recent_chats[0])

        self.win.protocol("WM_DELETE_WINDOW", lambda arg=broadcast_queue: self.close_window(arg))
        self.win.mainloop()

    def send_message(self, direct_queue):
        index = self.friends_listbox.curselection()[0]
        guid = self.friends_listbox.itemcget(index, "value")
        print(guid)
        
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

    # def switch_chat_history(self, friend_name):
    #     self.chathistory_text.config(state="normal")
    #     self.friendname_label.config(text=friend_name)
    #     chat_history = self.chat_histories.get(friend_name, [])
    #     self.chathistory_text.delete("1.0", tkinter.END)
    #     self.chathistory_text.insert(tkinter.END, "\n".join(chat_history))
    #     self.chathistory_text.config(state="disabled")
    
    def switch_chat_history(self, guid):
        self.chathistory_text.config(state="normal")
        self.friendname_label.config(text=self.online[guid])
        chat_history = self.fetch_history()
        self.chathistory_text.delete("1.0", tkinter.END)
        self.chathistory_text.insert(tkinter.END, "\n".join(chat_history))
        self.chathistory_text.config(state="disabled")
        
    def fetch_history(self):
        # TODO fetch all rows of the table
        pass

    def close_window(self, broadcast_queue):
        broadcast_queue.put((BROADCAST_IP, MessageID.OFFLINE, None))
        self.win.destroy()
        time.sleep(2)
        os._exit(1)


client = Client()
