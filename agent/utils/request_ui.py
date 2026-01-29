import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import hashlib
import os
import httpx
import sys
from pathlib import Path

class UploadRequestApp:
    def __init__(self, dashboard_url, api_key):
        self.dashboard_url = dashboard_url
        self.api_key = api_key
        
        self.root = tk.Tk()
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
        
        # File Section
        file_frame = tk.Frame(self.root, bg="#09090b", padx=20)
        file_frame.pack(fill="x")
        
        tk.Label(file_frame, text="Select File to Upload:", bg="#09090b", foreground="#71717a").pack(anchor="w")
        
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
        
        # Destination
        dest_frame = tk.Frame(self.root, bg="#09090b", padx=20)
        dest_frame.pack(fill="x")
        
        tk.Label(dest_frame, text="Destination Website (optional):", bg="#09090b", foreground="#71717a").pack(anchor="w")
        self.dest_var = tk.StringVar()
        dest_entry = tk.Entry(dest_frame, textvariable=self.dest_var, bg="#18181b", fg="#ffffff", border=0, highlightthickness=1, highlightbackground="#27272a")
        dest_entry.pack(fill="x", pady=5, ipady=5)
        
        # Submit
        self.btn_submit = tk.Button(self.root, text="SUBMIT REQUEST", command=self._submit, bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", border=0, font=("Inter", 11, "bold"), pady=10)
        self.btn_submit.pack(fill="x", padx=20, pady=20)

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
