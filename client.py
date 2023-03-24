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

TCP_PORT = 8002
UDP_PORT = 8001
BROADCAST_IP = "255.255.255.255"

class Client:
    chat_histories = {
        "Friend 1": ["Hi", "How are you?", "I'm fine, thanks."],
        "Friend 2": ["Hey", "What's up?", "Not much, just chilling."],
        "Friend 3": ["Yo", "Sup?", "Nm, hbu?"]}
    online = {} # client addr: username
    my_friends = []

    def __init__(self):
        # udp_socket = self.open_udp()
        # tcp_socket = self.open_tcp()
        broadcast_queue = queue.Queue()

        # tcplistener_thread = threading.Thread(target=self.recv_tcp)
        # tcplistener_thread.starT()

        # udplistener_thread = threading.Thread(target=self.recv_udp, args=(udp_socket, broadcast_queue))
        # udplistener_thread.start()

        # broadcast_queue.put((BROADCAST_IP, MessageID.ONLINE, None))

        # udpsender_thread = threading.Thread(target=self.send_udp, args=(udp_socket, broadcast_queue))
        # udpsender_thread.start()

        gui_thread = threading.Thread(target=self.gui_loop, args=(broadcast_queue, ))
        gui_thread.start()

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
    
    def recv_tcp(self, tcp_socket):
        inputs = [tcp_socket, ]
        outputs = []
        
        while True:
            try:
                readable, writable, exceptional = select.select(
                    inputs + self.my_friends,
                    outputs,
                    inputs + self.my_friends)
                
                for sock in readable:
                    if sock is tcp_socket:              # new chat, someone binded successfully
                        pass
                    elif sock in self.my_friends:
                        pass         
            except Exception as e:
                print("SOMETHING IS BAD")
                print(e)
                sys.exit(0)      
            

    def recv_udp(self, udp_socket, broadcast_queue):
        while True:
            #try:
            data, addr = udp_socket.recvfrom(2048)
            
            if addr[0] != socket.gethostbyname(socket.gethostname()):
                print(f"Received broadcast from {addr}: {data.decode()}")
                message_dict = json.loads(data.decode())
                message = Message(**message_dict)
                if message.messageID is MessageID.ONLINE:
                    self.online[addr] = message.sender
                    if not message.message:
                        broadcast_queue.put((addr[0], MessageID.ONLINE, "ACK"))
                elif message.messageID is MessageID.OFFLINE:
                    del self.online[addr]
                elif message.messageID is MessageID.START:
                    pass # someone wants to start TCP
                print(self.online)
            # except Exception as e:
            #     print(e)

            # filter messages
    
    def send_udp(self, udp_socket, broadcast_queue):
        while True:
            if broadcast_queue.qsize() > 0:
                addrIP, messageID, message = broadcast_queue.get(block=False)
                message = Message(messageID, "vickyko", message)
                message_dict = vars(message)
                message_json = json.dumps(message_dict)
                udp_socket.sendto(message_json.encode(), (addrIP, UDP_PORT))
            time.sleep(500)
        
    def gui_loop(self, broadcast_queue):
        width = 1200
        height = 750
        self.win = tkinter.Tk()
        self.win.geometry(f"{width}x{height}")
        self.win.resizable(False, False)
        self.win.title("Definitely Not Discord")
        tkinter.Widget

        left_frame = tkinter.Frame(self.win, width=int(width/4), height=height, bg="#2C2D31")
        left_frame.pack(side="left")

        options_frame = tkinter.Frame(left_frame, width=20, height=20, bg="#2C2D31")
        options_frame.pack(side="top")

        username_text = tkinter.Text(options_frame, width=20, height=1)
        username_text.pack(side="left", padx=10, pady=10)
        username_text.insert(tkinter.END, "User")

        newchat_button = tkinter.Button(options_frame, text="New Chat", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF")
        newchat_button.pack(side="right", padx=10, pady=10)

        friends_listbox = tkinter.Listbox(left_frame, bg="#2C2D31", fg="#FFFFFF", width=30, height=50, borderwidth=0, highlightthickness=0, font=12, selectbackground="#414249", activestyle="none")
        friends_listbox.pack(side="bottom", padx=10, pady=10)
        friends_listbox.bind('<<ListboxSelect>>', lambda event=None: self.switch_chat_history(friends_listbox.get(friends_listbox.curselection())))

        for friend_name in self.chat_histories.keys():
            friends_listbox.insert(tkinter.END, friend_name)

        right_frame = tkinter.Frame(self.win, width=int(3*width/4), height=height, bg="#323338")
        right_frame.pack(side="right")

        name_frame = tkinter.Frame(right_frame, width=20, height=50, bg="#323338")
        name_frame.pack(side="top", pady=5)

        circle_canvas = tkinter.Canvas(name_frame, width=15, height=15, bg="#323338", borderwidth=0, highlightthickness=0)
        circle_canvas.pack(side="left", padx=2, pady=2)
        circle_canvas.create_oval(2, 2, 15, 15, fill="Green")

        self.friendname_label = tkinter.Label(name_frame, text="", bg="#323338", fg="#FFFFFF", font=12)
        self.friendname_label.pack(side="right", padx=2, pady=2)

        self.chathistory_text = tkinter.Text(right_frame, width=int(3*width/4), height=40)
        self.chathistory_text.pack(side="top", padx=10, pady=10, expand=True)
        # self.chathistory_text = tkinter.Text()
        
        input_frame = tkinter.Frame(right_frame, bg="#323338", width=int(3*width/4), height=51)
        input_frame.pack(side="bottom", padx=10, pady=10)
        
        input_text = tkinter.Text(input_frame, width=100, height=0)
        input_text.pack(side="left")
        
        sendinput_button = tkinter.Button(input_frame, text="Send", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF")
        sendinput_button.pack(side="right")

        friends_listbox.select_set(0)
        self.switch_chat_history(list(self.chat_histories.keys())[0])

        self.win.protocol("WM_DELETE_WINDOW", lambda arg=broadcast_queue: self.close_window(arg))
        self.win.mainloop()

    # deal with selection outside of listbox
    def switch_chat_history(self, friend_name):
        self.friendname_label.config(text=friend_name)
        chat_history = self.chat_histories.get(friend_name, [])
        self.chathistory_text.delete("1.0", tkinter.END)
        self.chathistory_text.insert(tkinter.END, "\n".join(chat_history))

    def close_window(self, broadcast_queue):
        broadcast_queue.put((BROADCAST_IP, MessageID.OFFLINE, None))
        self.win.destroy()
        time.sleep(2)
        os._exit(1)


client = Client()
