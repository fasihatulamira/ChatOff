"""Forced or voluntary password change dialog."""
import customtkinter as ctk
from tkinter import messagebox

from auth import change_password


class ChangePasswordWindow(ctk.CTk):
    def __init__(self, username: str, *, required: bool = True):
        super().__init__()
        self.username = username
        self.required = required
        self.success = False

        self.title("Change Password — ChatOff")
        self.geometry("480x420")
        self.resizable(False, False)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"480x420+{(sw-480)//2}+{(sh-420)//2}")

        if required:
            self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        hero = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1565C0", "#0D1B2A"))
        hero.pack(fill="x")
        ctk.CTkLabel(hero, text="🔐  Password Change Required", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack(pady=(20, 4))
        ctk.CTkLabel(
            hero,
            text="You must set a new password before continuing.",
            font=ctk.CTkFont(size=13),
            text_color="#90CAF9",
        ).pack(pady=(0, 16))

        body = ctk.CTkFrame(self, corner_radius=16)
        body.pack(fill="both", expand=True, padx=24, pady=16)

        self.current_entry = self._field(body, "Current password", show="•")
        self.new_entry = self._field(body, "New password (min. 6 characters)", show="•")
        self.confirm_entry = self._field(body, "Confirm new password", show="•")
        self.confirm_entry.bind("<Return>", lambda e: self._submit())

        self.error_label = ctk.CTkLabel(body, text="", text_color="#FF6B6B", wraplength=380)
        self.error_label.pack(pady=(4, 8))

        ctk.CTkButton(body, text="Save New Password", height=44, font=ctk.CTkFont(weight="bold"), command=self._submit).pack(fill="x", pady=(4, 0))
        if not required:
            ctk.CTkButton(body, text="Cancel", height=36, fg_color="transparent", command=self._on_cancel).pack(fill="x", pady=(8, 0))

    def _field(self, parent, label, show=""):
        ctk.CTkLabel(parent, text=label, anchor="w", font=ctk.CTkFont(size=13)).pack(fill="x", padx=8, pady=(10, 2))
        entry = ctk.CTkEntry(parent, height=40, show=show, font=ctk.CTkFont(size=13))
        entry.pack(fill="x", padx=8)
        return entry

    def _submit(self):
        current = self.current_entry.get()
        new_pw = self.new_entry.get()
        confirm = self.confirm_entry.get()

        if not current or not new_pw or not confirm:
            self.error_label.configure(text="Please fill in all fields.")
            return
        if new_pw != confirm:
            self.error_label.configure(text="New passwords do not match.")
            return
        if len(new_pw) < 6:
            self.error_label.configure(text="New password must be at least 6 characters.")
            return
        if new_pw == "admin123":
            self.error_label.configure(text="Please choose a password other than the default.")
            return

        ok, msg = change_password(self.username, current, new_pw)
        if ok:
            self.success = True
            messagebox.showinfo("Success", "Password updated successfully.")
            self.destroy()
        else:
            self.error_label.configure(text=msg)

    def _on_cancel(self):
        if self.required:
            if messagebox.askyesno("Exit", "You must change your password to use ChatOff. Exit instead?"):
                self.success = False
                self.destroy()
        else:
            self.destroy()
