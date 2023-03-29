import threading
import tkinter
import queue

WIDTH = 1200
HEIGHT = 750

class GUIManager(threading.Thread):
    def __init__(self, mediator):
        self.mediator = mediator
        threading.Thread.__init__(self)

    def run(self):
        self.win = tkinter.Tk()
        self.win.geometry(f"{WIDTH}x{HEIGHT}")
        self.win.resizable(False, False)
        self.win.title("Definitely Not Discord")

        left_frame = tkinter.Frame(self.win, width=int(WIDTH/4), height=HEIGHT, bg="#2C2D31")
        left_frame.pack(side="left")

        newchat_button = tkinter.Button(left_frame, text="New Chat", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF")
        newchat_button.pack(side="top", padx=10, pady=10)

        self.friends_listbox = tkinter.Listbox(left_frame, bg="#2C2D31", fg="#FFFFFF", width=32, height=50, borderwidth=0, highlightthickness=0, font=12, selectbackground="#414249", activestyle="none", exportselection=False)
        self.friends_listbox.pack(side="bottom", padx=10, pady=10)
        self.friends_listbox.bind('<<ListboxSelect>>', lambda event=None: self.switch_chat_history(self.recent_chats[self.friends_listbox.curselection()]))

        right_frame = tkinter.Frame(self.win, width=int(3*WIDTH/4), height=HEIGHT, bg="#323338")
        right_frame.pack(side="right")

        placeholder_frame = tkinter.Frame(right_frame, width=int(3*WIDTH/4), height=HEIGHT, bg="#323338")
        #placeholder_frame.pack(side="top", pady=5)
        placeholder_frame.pack_forget()

        name_frame = tkinter.Frame(placeholder_frame, width=20, height=40, bg="#323338")
        name_frame.pack(side="top", pady=5)

        circle_canvas = tkinter.Canvas(name_frame, width=15, height=15, bg="#323338", borderwidth=0, highlightthickness=0)
        circle_canvas.pack(side="left", padx=2)
        circle_canvas.create_oval(2, 2, 15, 15, fill="Green")

        self.friendname_label = tkinter.Label(name_frame, text="", bg="#323338", fg="#FFFFFF", font=12)
        self.friendname_label.pack(side="right", padx=2)

        self.chathistory_text = tkinter.Text(placeholder_frame, width=110, height=41, bg="#323338", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        self.chathistory_text.pack(side="top", padx=10, pady=5)

        input_frame = tkinter.Frame(placeholder_frame, bg="#323338", width=540, height=50)
        input_frame.pack(side="bottom", padx=10, pady=6)
        
        input_text = tkinter.Text(input_frame, width=100, height=1, bg="#414249", fg="#FFFFFF", borderwidth=0, highlightthickness=0)
        input_text.pack(side="left")
        
        sendinput_button = tkinter.Button(input_frame, text="Send", bg="#414249", fg="#FFFFFF", activebackground="#414249", activeforeground="#FFFFFF", command= lambda: self.send_message(input_text.get("1.0", tkinter.END), self.friends_listbox.curselection()))
        sendinput_button.pack(side="right")

        self.win.mainloop()
        
        while True:
            result = self.mediator.get_receive_message()
            if result is not None:
                sender_id = result[0]
                message = result[1]
                # TODO update GUI 

    def close_window(self):
        self.win.destroy()
        #self.peer.close_window()

    def update_recents_list(self):
        pass

    def update_right_frame(self, is_online, username, chat_list):
        pass
    
    def send_message(self, message, send_to_index):
        # TODO update gui
        # TODO send to mediator
        self.mediator.send_message(send_to_index, message)