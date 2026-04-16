#GUI
import customtkinter as ctk
import threading
from tkinter import messagebox
from chatbot import get_response

# Set UI theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class OfflineChatbot(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Offline Chatbot 🤖")
        self.geometry("800x600")

        # Configure architecture
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ===== SIDEBAR =====
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="ChatOff AI", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.model_label = ctk.CTkLabel(self.sidebar_frame, text="Select Model:", anchor="w")
        self.model_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        
        self.model_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["llama3", "mistral", "phi3"])
        self.model_optionemenu.grid(row=2, column=0, padx=20, pady=(10, 10))
        self.model_optionemenu.set("llama3")

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))

        # ===== MAIN CHAT =====
        self.chat_area = ctk.CTkTextbox(self, font=ctk.CTkFont(size=14))
        self.chat_area.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")
        self.chat_area.configure(state="disabled")

        # ===== INPUT AREA =====
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...", height=40)
        self.entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_button = ctk.CTkButton(self.input_frame, text="Send", width=100, height=40, font=ctk.CTkFont(weight="bold"), command=self.send_message)
        self.send_button.grid(row=0, column=1)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def append_chat(self, sender, message):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"\n{sender}: ", "bold")
        self.chat_area.insert("end", f"{message}\n")
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")

    def send_message(self):
        user_msg = self.entry.get()
        if not user_msg.strip():
            return

        self.entry.delete(0, "end")
        self.append_chat("You", user_msg)
        
        self.send_button.configure(state="disabled")
        threading.Thread(target=self.process_ai_response, args=(user_msg,), daemon=True).start()

    def process_ai_response(self, prompt):
        model = self.model_optionemenu.get()
        try:
            self.after(0, lambda: self.chat_area.configure(state="normal"))
            self.after(0, lambda: self.chat_area.insert("end", "\nBot: ", "bold"))
            
            for chunk in get_response(prompt, model):
                self.after(0, lambda c=chunk: self.update_streaming_chat(c))

            self.after(0, lambda: self.chat_area.insert("end", "\n"))
            self.after(0, lambda: self.chat_area.configure(state="disabled"))
            self.after(0, lambda: self.chat_area.see("end"))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.after(0, lambda: self.append_chat("System", f"Error: {error_msg}"))
        finally:
            self.after(0, lambda: self.send_button.configure(state="normal"))

    def update_streaming_chat(self, content):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", content)
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
