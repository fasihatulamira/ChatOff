# Import CustomTkinter (modern UI version of Tkinter)
import customtkinter as ctk  

# Import threading so chatbot response can run in background (no UI freeze)
import threading  

# Import Ollama to communicate with local AI models
import ollama  

# Import messagebox for popup error messages
from tkinter import messagebox  

# Import login window and database initialiser
from auth import init_db
from login import LoginWindow


# Set UI theme to Dark mode
ctk.set_appearance_mode("Dark")

# Set default color theme (blue buttons, etc.)
ctk.set_default_color_theme("blue")


# Create main app class (inherits from CTk window)
class OfflineChatbot(ctk.CTk):

    def __init__(self):
        super().__init__()  # Initialize parent class (window)

        # Set window title
        self.title("Offline Chatbot 🤖")

        # Auto fullscreen: detect screen resolution and fill it
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")
        self.state("zoomed")  # also maximise for taskbar-aware platforms


        # Configure grid layout (for responsive resizing)
        self.grid_columnconfigure(1, weight=1)  # column 1 expands
        self.grid_rowconfigure(0, weight=1)     # row 0 expands


        # ===== SIDEBAR (LEFT PANEL) =====
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        # Allow spacing inside sidebar
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # App title in sidebar
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="ChatOff AI", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))


        # Label for model selection
        self.model_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Select Model:", 
            anchor="w"
        )
        self.model_label.grid(row=1, column=0, padx=20, pady=(10, 0))
        

        # Dropdown menu to choose AI model
        self.model_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["llama3", "mistral", "phi3"]
        )
        self.model_optionemenu.grid(row=2, column=0, padx=20, pady=(10, 10))

        # Set default model
        self.model_optionemenu.set("llama3")


        # Label for appearance mode
        self.appearance_mode_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Appearance:", 
            anchor="w"
        )
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))


        # Dropdown to change theme (Dark / Light / System)
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode_event  # call function when changed
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))


        # ===== MAIN CHAT AREA =====
        self.chat_area = ctk.CTkTextbox(
            self, 
            font=ctk.CTkFont(size=14)
        )
        self.chat_area.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        # Disable editing (user cannot type here)
        self.chat_area.configure(state="disabled")


        # ===== INPUT AREA =====
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        # Make input stretch horizontally
        self.input_frame.grid_columnconfigure(0, weight=1)


        # Text input box
        self.entry = ctk.CTkEntry(
            self.input_frame, 
            placeholder_text="Type your message here...", 
            height=40
        )
        self.entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        # Press Enter = send message
        self.entry.bind("<Return>", lambda e: self.send_message())


        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame, 
            text="Send", 
            width=100, 
            height=40, 
            font=ctk.CTkFont(weight="bold"), 
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1)


    # ===== CHANGE THEME FUNCTION =====
    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)


    # ===== DISPLAY MESSAGE IN CHAT =====
    def append_chat(self, sender, message):
        self.chat_area.configure(state="normal")  # enable editing

        # Insert sender name (bold style)
        self.chat_area.insert("end", f"\n{sender}: ", "bold")

        # Insert message text
        self.chat_area.insert("end", f"{message}\n")

        self.chat_area.configure(state="disabled")  # disable again
        self.chat_area.see("end")  # auto scroll to bottom


    # ===== SEND MESSAGE FUNCTION =====
    def send_message(self):
        user_msg = self.entry.get()  # get input text

        # If empty → do nothing
        if not user_msg.strip():
            return

        self.entry.delete(0, "end")  # clear input box

        # Show user message in chat
        self.append_chat("You", user_msg)
        
        # Disable button to prevent spam clicking
        self.send_button.configure(state="disabled")

        # Run AI response in separate thread (avoid freezing UI)
        threading.Thread(
            target=self.get_ollama_response, 
            args=(user_msg,), 
            daemon=True
        ).start()


    # ===== GET RESPONSE FROM OLLAMA =====
    def get_ollama_response(self, prompt):
        model = self.model_optionemenu.get()  # get selected model

        try:
            # Prepare UI for bot response
            self.after(0, lambda: self.chat_area.configure(state="normal"))
            self.after(0, lambda: self.chat_area.insert("end", "\nBot: ", "bold"))
            
            # Stream response from Ollama
            stream = ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True,  # streaming mode (word by word)
            )

            # Loop through streamed chunks
            for chunk in stream:
                content = chunk['message']['content']

                # Update UI safely from thread
                self.after(0, lambda c=content: self.update_streaming_chat(c))

            # Finish formatting
            self.after(0, lambda: self.chat_area.insert("end", "\n"))
            self.after(0, lambda: self.chat_area.configure(state="disabled"))
            self.after(0, lambda: self.chat_area.see("end"))


        except Exception as e:
            error_msg = str(e)

            # Show popup error
            self.after(0, lambda: messagebox.showerror(
                "Ollama Error", 
                f"Could not connect to Ollama:\n{error_msg}"
            ))

            # Also display in chat
            self.after(0, lambda: self.append_chat("System", f"Error: {error_msg}"))


        finally:
            # Re-enable send button
            self.after(0, lambda: self.send_button.configure(state="normal"))


    # ===== UPDATE STREAMED TEXT =====
    def update_streaming_chat(self, content):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", content)  # append new chunk
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")


# ===== RUN APP =====
if __name__ == "__main__":
    # Ensure the users table exists before anything opens
    init_db()

    # Launch the Login window first; it will open the chatbot on success
    login = LoginWindow()
    login.mainloop()