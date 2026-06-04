# Import login window and database initializer
from login import LoginWindow
from GUI import OfflineChatbot

# ===== RUN APP =====
if __name__ == "__main__":
    while True:
        # Launch the Login window first
        login = LoginWindow()
        login.mainloop()
        
        # Check if the user logged in successfully
        if getattr(login, "logged_in_username", None):
            username = login.logged_in_username
            user_name = login.logged_in_user
            
            # Launch the chatbot main window
            app = OfflineChatbot(user_name=user_name, username=username)
            app.mainloop()
            
            # Check if chatbot logged out (user wants to log in as someone else)
            if getattr(app, "logged_out", False):
                continue
            else:
                break
        else:
            # Login window was closed without logging in (X button clicked)
            break