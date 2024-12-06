import socket
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import os
import json

class FileClientApp:
    def __init__(self, master):
        # Initialize the GUI components and set up the main window
        self.master = master
        self.master.title("File Client")
        self.master.geometry("600x500")

        # Connection Frame
        conn_frame = ttk.LabelFrame(master, text="Server Connection")
        conn_frame.pack(padx=10, pady=5, fill="x")

        # Input fields for user name, server host, and port number
        ttk.Label(conn_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(conn_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Host:").grid(row=1, column=0, padx=5, pady=5)
        self.host_entry = ttk.Entry(conn_frame)
        # self.host_entry.insert(0, "localhost")  # Default host is set to localhost useful while dev
        self.host_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=2, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(conn_frame)
        # self.port_entry.insert(0, "5000")  # Default port is set to 5000 useful for developinbg
        self.port_entry.grid(row=2, column=1, padx=5, pady=5)

        # Connect and Disconnect buttons
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.disconnect_button = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect, state='disabled')
        self.disconnect_button.grid(row=3, column=11, columnspan=2, pady=10)

        # Actions Frame
        actions_frame = ttk.LabelFrame(master, text="Actions")
        actions_frame.pack(padx=10, pady=5, fill="x")

        # Buttons for file actions - Upload, Download, List, and Delete
        self.upload_button = ttk.Button(actions_frame, text="Upload File", command=self.upload_file, state='disabled')
        self.upload_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.download_button = ttk.Button(actions_frame, text="Download File", command=self.download_file, state='disabled')
        self.download_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.list_button = ttk.Button(actions_frame, text="List Files", command=self.list_files, state='disabled')
        self.list_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.delete_button = ttk.Button(actions_frame, text="Delete File", command=self.delete_file, state='disabled')
        self.delete_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Log Frame - Displays activity log of client actions
        log_frame = ttk.LabelFrame(master, text="Activity Log")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=20)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        self.socket = None  # Socket variable to hold the connection

    # Method to log messages in the activity log
    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    # Method to connect to the server
    def connect(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter your name")
                return

            host = self.host_entry.get().strip()
            port = int(self.port_entry.get())

            # Create and connect socket to server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))

            # Send client name to the server
            self.socket.send(name.encode())

            # Enable action buttons after successful connection
            self.upload_button.config(state='normal')
            self.download_button.config(state='normal')
            self.list_button.config(state='normal')
            self.delete_button.config(state='normal')
            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')

            self.log_message(f"Connected to server at {host}:{port}")

        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")
            self.log_message(f"Connection error: {str(e)}")

    # Method to disconnect from the server
    def disconnect(self):
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
                self.log_message(f"Disconnected from server.")

                # Disable action buttons after disconnection
                self.upload_button.config(state='disabled')
                self.download_button.config(state='disabled')
                self.list_button.config(state='disabled')
                self.delete_button.config(state='disabled')
                self.connect_button.config(state='normal')
                self.disconnect_button.config(state='disabled')
        except Exception as e:
            self.log_message(f"Disconnect error: {str(e)}")

    # Method to upload a file to the server
    def upload_file(self):
        # Open file dialog to select file for upload
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not file_path:
            return

        try:
            filename = os.path.basename(file_path)

            # Send upload command and file details to server
            self.socket.send(json.dumps({
                "action": "upload",
                "filename": filename
            }).encode())

            # Send file size and data
            file_size = os.path.getsize(file_path)
            self.socket.send(str(file_size).encode().ljust(10))

            # Read file and send data in chunks
            with open(file_path, 'rb') as f:
                while data := f.read(4096):
                    self.socket.send(data)

            # Receive server response
            response = self.socket.recv(1024).decode()
            if response == "SUCCESS":
                self.log_message(f"File {filename} uploaded successfully")
            else:
                self.log_message(f"Upload failed: {response}")

        except Exception as e:
            self.log_message(f"Upload error: {str(e)}")

    # Method to list files available on the server
    def list_files(self):
        try:
            # Send list command to server
            self.socket.send(json.dumps({"action": "list"}).encode())
            response = self.socket.recv(4096).decode()
            files = json.loads(response)

            # Display file list in a new window
            top = tk.Toplevel(self.master)
            top.title("Server Files")
            top.geometry("300x400")

            listbox = tk.Listbox(top)
            listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            for file in files:
                listbox.insert(tk.END, file)

            self.log_message("Retrieved file list from server")

        except Exception as e:
            self.log_message(f"List error: {str(e)}")

    # Method to download a file from the server
    def download_file(self):
        filename = simpledialog.askstring("Download", "Enter the filename to download:")
        if not filename:
            return

        try:
            # Send download command to server
            self.socket.send(json.dumps({
                "action": "download",
                "filename": filename
            }).encode())

            # Receive file size from server
            file_size = int(self.socket.recv(10).strip())

            # Open file dialog to select save location
            save_path = filedialog.asksaveasfilename(
                initialfile = filename,
                defaultextension = ".txt",
                filetypes = [("Text Files", "*.txt")]
            )
            if not save_path:
                return

            # Receive and save file data
            received = 0
            with open(save_path, 'wb') as f:
                while received < file_size:               # Keep up till whole file is recieved
                    data = self.socket.recv(min(4096, file_size - received))
                    if not data:
                        break
                    f.write(data)
                    received += len(data)

            self.log_message(f"File {filename} downloaded successfully")

        except Exception as e:
            self.log_message(f"Download error: {str(e)}")

    # Method to delete a file from the server
    def delete_file(self):
        filename = simpledialog.askstring("Delete", "Enter the filename to delete:")
        if not filename:
            return

        try:
            # Send delete command to server
            self.socket.send(json.dumps({
                "action": "delete",
                "filename": filename
            }).encode())

            # Receive server response
            response = self.socket.recv(1024).decode()
            if response == "SUCCESS":
                self.log_message(f"File {filename} deleted successfully")
            else:
                self.log_message(f"Delete failed: {response}")

        except Exception as e:
            self.log_message(f"Delete error: {str(e)}")

# Main function
def main():
    root = tk.Tk()
    app = FileClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
