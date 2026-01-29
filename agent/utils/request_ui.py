import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import hashlib
import os
import httpx
import sys
import subprocess
from pathlib import Path

class UploadRequestApp:
    def __init__(self, dashboard_url, api_key):
        self.dashboard_url = dashboard_url
        self.api_key = api_key
        
        self.root = tk.Tk()
        self.dest_var = tk.StringVar()
        self.root.title("Endpoint Security - Request Upload")
        self.root.geometry("500x450")
        self.root.configure(bg="#09090b") # zinc-950
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#09090b", foreground="#a1a1aa", font=("Inter", 10))
        self.style.configure("TButton", font=("Inter", 10, "bold"))
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Header
        header = tk.Label(self.root, text="UPLOAD PERMISSION REQUEST", bg="#09090b", foreground="#ffffff", font=("Inter", 14, "bold"), pady=20)
        header.pack()
        
        # Check Status Section
        status_frame = tk.Frame(self.root, bg="#18181b", padx=20, pady=10)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_label = tk.Label(status_frame, text="Current Status: Checking...", bg="#18181b", foreground="#a1a1aa", font=("Inter", 9))
        self.status_label.pack(side="left")
        
        self.btn_refresh = tk.Button(status_frame, text="Refresh Status", command=self._check_approvals, bg="#27272a", fg="#ffffff", border=0, font=("Inter", 8))
        self.btn_refresh.pack(side="right")

        self.btn_unlock = tk.Button(self.root, text="🔓 START APPROVED UPLOAD", command=self._unlock_system, bg="#059669", fg="#ffffff", activebackground="#047857", border=0, font=("Inter", 11, "bold"), pady=10)
        self.btn_unlock.pack(fill="x", padx=20, pady=5)
        self.btn_unlock.pack_forget() # Hidden by default
        
        # Separator
        tk.Frame(self.root, height=1, bg="#27272a").pack(fill="x", padx=20, pady=15)
        
        # File Section
        file_frame = tk.Frame(self.root, bg="#09090b", padx=20)
        file_frame.pack(fill="x")
        
        tk.Label(file_frame, text="Request New File:", bg="#09090b", foreground="#71717a").pack(anchor="w")
        
        self.file_path_var = tk.StringVar()
        entry = tk.Entry(file_frame, textvariable=self.file_path_var, bg="#18181b", fg="#ffffff", insertbackground="#ffffff", border=0, highlightthickness=1, highlightbackground="#27272a")
        entry.pack(fill="x", pady=5, ipady=5)
        
        btn_browse = tk.Button(file_frame, text="Browse File", command=self._browse_file, bg="#27272a", fg="#ffffff", activebackground="#3f3f46", border=0, padx=10, pady=5)
        btn_browse.pack(anchor="e")
        
        # Justification
        just_frame = tk.Frame(self.root, bg="#09090b", padx=20, pady=10)
        just_frame.pack(fill="x")
        
        tk.Label(just_frame, text="Business Justification:", bg="#09090b", foreground="#71717a").pack(anchor="w")
        self.justification_text = tk.Text(just_frame, height=4, bg="#18181b", fg="#ffffff", insertbackground="#ffffff", border=0, highlightthickness=1, highlightbackground="#27272a", font=("Inter", 10))
        self.justification_text.pack(fill="x", pady=5)
        
        # Submit
        self.btn_submit = tk.Button(self.root, text="SUBMIT NEW REQUEST", command=self._submit, bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", border=0, font=("Inter", 11, "bold"), pady=10)
        self.btn_submit.pack(fill="x", padx=20, pady=15)
        
        self._check_approvals()

    def _check_approvals(self):
        try:
            headers = {"X-API-Key": self.api_key}
            response = httpx.get(f"{self.dashboard_url}/api/v1/agent/uploads/approved", headers=headers)
            if response.status_code == 200:
                hashes = response.json().get('approved_hashes', [])
                if hashes:
                    self.status_label.config(text=f"✅ {len(hashes)} files approved!", fg="#10b981")
                    self.btn_unlock.pack(fill="x", padx=20, pady=5, before=self.btn_submit)
                else:
                    self.status_label.config(text="⏳ No approved files found.", fg="#a1a1aa")
                    self.btn_unlock.pack_forget()
        except Exception:
            self.status_label.config(text="❌ Error connecting to server", fg="#ef4444")

    def _unlock_system(self):
        """Tell the main agent to unlock using the specifically approved file."""
        try:
            path = self.file_path_var.get()
            if not path or not os.path.exists(path):
                messagebox.showerror("Error", "Selected file not found.")
                return
                
            file_hash = self._get_hash(path)
            
            python_exe = sys.executable
            # Ensure we get the absolute path to agent/main.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            main_script = os.path.join(os.path.dirname(current_dir), "main.py")
            
            # Pass the path and hash to the unlock command
            # Using a list with Popen is the safest way to handle spaces in paths on Windows
            subprocess.Popen([python_exe, main_script, "unlock-upload", path, file_hash], 
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            messagebox.showinfo("Security Window", "UPLOAD UNLOCKED!\n\n1. Go to your browser.\n2. Open the 'SecureUploadGateway' folder on your C: drive.\n3. Pick your file and upload.\n\nYou have 45 seconds.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unlock: {e}")

    def _browse_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.file_path_var.set(filename)

    def _get_hash(self, path):
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _submit(self):
        path = self.file_path_var.get()
        just = self.justification_text.get("1.0", "end-1c").strip()
        
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid file")
            return
        if not just:
            messagebox.showerror("Error", "Please provide a justification")
            return
            
        self.btn_submit.config(state="disabled", text="SUBMITTING...")
        
        try:
            file_info = Path(path)
            payload = {
                "file_name": file_info.name,
                "file_path": str(file_info.absolute()),
                "file_hash": self._get_hash(path),
                "file_size": os.path.getsize(path),
                "justification": just,
                "destination_site": self.dest_var.get() or None
            }
            
            headers = {"X-API-Key": self.api_key}
            response = httpx.post(f"{self.dashboard_url}/api/v1/agent/uploads/request", json=payload, headers=headers)
            
            if response.status_code in (200, 201):
                messagebox.showinfo("Success", "Request submitted successfully. Please wait for administrator approval.")
                self.root.destroy()
            else:
                messagebox.showerror("Error", f"Failed to submit: {response.text}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.btn_submit.config(state="normal", text="SUBMIT REQUEST")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # In production, these are passed from the main agent
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    
    app = UploadRequestApp(args.url, args.key)
    app.run()
