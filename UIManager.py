import threading
import tkinter
from message import *

WIDTH = 1200
HEIGHT = 750

class UIManager(threading.Thread):
    def __init__(self, mediator):
        self.mediator = mediator
        threading.Thread.__init__(self)

    def run(self):
        self.win = tkinter.Tk()
        self.win.resizable(False, False)
        self.win.title("Definitely Not Discord")
        self.win.geometry(f"{WIDTH}x{HEIGHT}")

        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()
        x_coord = int((screen_width / 2) - (WIDTH / 2))
        y_coord = int((screen_height / 2) - (HEIGHT / 2))
        self.win.geometry(f"+{x_coord}+{y_coord}")

        left_frame = tkinter.Frame(self.win, width=int(WIDTH/4), height=HEIGHT, bg="#2C2D31")
        left_frame.pack(side="left")

        newchat_button = tkinter.Button(left_frame, text="New Chat", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF", command=self.show_online_list)
        newchat_button.pack(side="top", padx=10, pady=10)

        self.recents_listbox = tkinter.Listbox(left_frame, bg="#2C2D31", fg="#FFFFFF", width=32, height=50, borderwidth=0, highlightthickness=0, font=12, selectbackground="#414249", activestyle="none", exportselection=False)
        self.recents_listbox.pack(side="bottom", padx=10, pady=10)
        self.recents_listbox.bind('<<ListboxSelect>>', lambda event=None: self.new_selection(self.recents_listbox.curselection()[0]))
        right_frame = tkinter.Frame(self.win, width=int(3*WIDTH/4), height=HEIGHT, bg="#323338")
        right_frame.pack(side="right")

        self.placeholder_frame = tkinter.Frame(right_frame, width=int(3*WIDTH/4), height=HEIGHT, bg="#323338")
        #placeholder_frame.pack(side="top", pady=5)
        self.placeholder_frame.pack_forget()

        name_frame = tkinter.Frame(self.placeholder_frame, width=20, height=40, bg="#323338")
        name_frame.pack(side="top", pady=5)

        self.status_canvas = tkinter.Canvas(name_frame, width=15, height=15, bg="#323338", borderwidth=0, highlightthickness=0)
        self.status_canvas.pack(side="left", padx=2)
        self.oval_id = self.status_canvas.create_oval(2, 2, 15, 15)

        self.peername_label = tkinter.Label(name_frame, text="", bg="#323338", fg="#FFFFFF", font=12)
        self.peername_label.pack(side="right", padx=2)

        self.chathistory_text = tkinter.Text(self.placeholder_frame, width=110, height=41, bg="#323338", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        self.chathistory_text.pack(side="top", padx=10, pady=5)
        self.chathistory_text.tag_configure("right", justify="right")
        self.chathistory_text.tag_configure("left", justify="left")

        input_frame = tkinter.Frame(self.placeholder_frame, bg="#323338", width=540, height=50)
        input_frame.pack(side="bottom", padx=10, pady=6)
        
        self.input_text = tkinter.Text(input_frame, width=90, height=1, bg="#414249", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        self.input_text.pack(side="left")
        
        sendinput_button = tkinter.Button(input_frame, text="Send", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF", command= lambda: self.send_message(self.input_text.get("1.0", tkinter.END).strip(), self.recents_listbox.curselection()))
        sendinput_button.pack(side="right")

        self.win.protocol("WM_DELETE_WINDOW", self.close_window)
        self.win.bind('<Return>', lambda event: self.send_message(self.input_text.get("1.0", tkinter.END).strip(), self.recents_listbox.curselection()))

        self.init_recents()

        self.win.after(100, self.catch_new_messages)
        self.win.mainloop()     
            
    def catch_new_messages(self):
        result = self.mediator.get_ui_action() # result = (action_type, peer_guid, peer_username, curr_index)
        if result is not None:
            if result[0] == Actions.OFFLINE or result[0] == Actions.ONLINE:
                self.change_status(result[1], result[3])
            elif result[0] == Actions.USERNAME:
                self.username_prompt()
            else:
                self.update_recents_list(result[3])
                if result[3] == 0:
                    self.update_right_frame(result[3])

        self.win.after(100, self.catch_new_messages)

    def close_window(self):
        self.win.destroy()
        self.mediator.close_window()

    def init_recents(self):
        self.recents_listbox.delete(0, tkinter.END)
        recent_list = self.mediator.get_peers_info()
        for row in recent_list:
            self.recents_listbox.insert(tkinter.END, row[1])

    def update_recents_list(self, curr_index):
        self.recents_listbox.delete(0, tkinter.END)
        recent_list = self.mediator.get_peers_info()
        for row in recent_list:
            self.recents_listbox.insert(tkinter.END, row[1])
        
        if curr_index is not None:
            self.recents_listbox.select_set(curr_index)

    def update_right_frame(self, index):
        self.placeholder_frame.pack(side="top", pady=5)
        peer_guid = self.mediator.get_index_guid(index)
        peer_username = self.recents_listbox.get(index)
        self.peername_label.config(text=peer_username)
        is_online = self.mediator.is_online(peer_guid)
        if is_online is True:
            self.status_canvas.itemconfig(self.oval_id, fill="Green")
        else:
            self.status_canvas.itemconfig(self.oval_id, fill="Grey")
        self.update_chat_history(peer_guid)
    
    def send_message(self, message, send_to_index):
        if len(message) > 0:
            self.input_text.delete("1.0", tkinter.END)

            if len(send_to_index) > 0: # selection
                send_to_index = send_to_index[0]
                peer_guid = self.mediator.get_index_guid(send_to_index)
                if self.mediator.is_online(peer_guid): # if online
                    if self.mediator.is_peer_connected(peer_guid): # if connected
                        self.mediator.put_tcp_action(Actions.MY_MESSAGE, peer_guid, self.mediator.get_online_username(peer_guid), MessageID.PERSONAL, message)
                    else: # if not connected
                        self.mediator.put_udp_action(MessageID.START, peer_guid, message)
                else: # if offline
                    self.chathistory_text.config(state="normal")
                    self.chathistory_text.insert(tkinter.END, "\n**** MESSAGE NOT SENT: PEER NOT ONLINE ****", "right") 
                    self.chathistory_text.config(state="disabled")
            else: # no selection
                peer_guid = self.mediator.get_draft_guid()
                if self.mediator.is_online(peer_guid) and self.mediator.is_peer_connected(peer_guid): # if connected
                    self.mediator.put_tcp_action(Actions.MY_MESSAGE, peer_guid, self.mediator.get_online_username(peer_guid), MessageID.PERSONAL, message)
                else: # if online only
                    self.mediator.put_udp_action(MessageID.START, peer_guid, message)

    def change_status(self, guid, curr_index):
        if curr_index is not None and self.mediator.get_index_guid(curr_index) == guid:
            is_online = self.mediator.is_online(guid)
            if is_online is True:
                self.status_canvas.itemconfig(self.oval_id, fill="Green")
            else:
                self.status_canvas.itemconfig(self.oval_id, fill="Grey")

    def new_selection(self, index):
        self.mediator.set_curr_index(index)
        self.update_right_frame(index)

    def update_chat_history(self, peer_guid):
        self.chathistory_text.config(state="normal")
        self.chathistory_text.delete("1.0", tkinter.END)
        chat_history = self.mediator.get_peer_history(peer_guid)
        for row in chat_history:
            if row[0] == str(peer_guid): # their message
                self.chathistory_text.insert(tkinter.END, "\n" + str(row[1]), "left")
            else: # my message
                self.chathistory_text.insert(tkinter.END, "\n" + str(row[1]), "right")
        self.chathistory_text.config(state="disabled")

    def show_online_list(self):
        self.online_popup = tkinter.Toplevel(self.win)
        self.online_popup.title("Peers Online")
        self.online_popup.resizable(False, False)
        self.online_popup.geometry("400x400")

        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()
        x_coord = int((screen_width / 2) - (400 / 2))
        y_coord = int((screen_height / 2) - (400 / 2))
        self.online_popup.geometry(f"+{x_coord}+{y_coord}")

        listbox = tkinter.Listbox(self.online_popup, exportselection=False, width=400, height=400, bg="#2C2D31", fg="#FFFFFF", borderwidth=0, highlightthickness=0, selectbackground="#414249", activestyle="none")
        listbox.pack()

        online_usernames = self.mediator.get_online_usernames()
        listbox.insert(tkinter.END, *online_usernames)

        listbox.bind('<<ListboxSelect>>', lambda event=None: self.new_chat(online_usernames, listbox.curselection()[0]))

    def new_chat(self, online_usernames, index):
        self.online_popup.destroy()
        self.placeholder_frame.pack(side="top", pady=5)
        self.recents_listbox.selection_clear(0, tkinter.END)
        self.peername_label.config(text=online_usernames[index])
        self.status_canvas.itemconfig(self.oval_id, fill="Green")
        self.chathistory_text.delete("1.0", tkinter.END)
        self.mediator.set_curr_index(None)
        self.chathistory_text.config(state="normal")
        self.chathistory_text.delete("1.0", tkinter.END)
        self.chathistory_text.config(state="disabled")
        self.mediator.set_draft_guid(index)

    def username_prompt(self):
        self.username_popup = tkinter.Toplevel(self.win)
        self.username_popup.title("Enter Username")
        self.username_popup.resizable(False, False)
        self.username_popup.grab_set()
        self.username_popup.geometry("250x100")
        self.username_popup.configure(bg="#323338")
        self.username_popup.attributes('-toolwindow', True)

        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()
        x_coord = int((screen_width / 2) - (250 / 2))
        y_coord = int((screen_height / 2) - (100 / 2))
        self.username_popup.geometry(f"+{x_coord}+{y_coord}")

        input_box = tkinter.Entry(self.username_popup, bg="#414249", fg="#FFFFFF", borderwidth=0, highlightthickness=0, width=30)
        input_box.pack(padx=5, pady=17)
        submit_button = tkinter.Button(self.username_popup, text="Submit", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF", command= lambda: self.submit_username(input_box.get().strip()))
        submit_button.pack()

    def submit_username(self, username):
        if len(username) > 0:
            self.username_popup.destroy()
            self.mediator.update_username(username)


