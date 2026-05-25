# Import login window and database initializer
from login import LoginWindow

# ===== RUN APP =====
if __name__ == "__main__":
    # Launch the Login window first; it will open the chatbot on success
    login = LoginWindow()
    login.mainloop()