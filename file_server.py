import socket
import threading
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class FileServerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("File Server")
        self.master.geometry("600x500")

        # Server Configuration Frame
        config_frame = ttk.LabelFrame(master, text="Server Configuration")
        config_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(config_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(config_frame, text="Folder:").grid(row=1, column=0, padx=5, pady=5)
        self.folder_label = ttk.Label(config_frame, text="No folder selected")
        self.folder_label.grid(row=1, column=1, padx=5, pady=5)

        self.browse_button = ttk.Button(config_frame, text="Browse", command=self.browse_folder)
        self.browse_button.grid(row=1, column=2, padx=5, pady=5)

        self.start_button = ttk.Button(config_frame, text="Start Server", command=self.start_server)
        self.start_button.grid(row=2, column=0, columnspan=3, pady=10)

        # Log Frame
        log_frame = ttk.LabelFrame(master, text="Server Log")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=20)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        # Initialize server variables
        self.server_socket = None
        self.storage_folder = ""
        self.is_running = False

    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.storage_folder = folder
            self.folder_label.config(text=folder)
            self.log_message(f"Storage folder set to: {folder}")

    def start_server(self):
        if not self.storage_folder:
            messagebox.showerror("Error", "Please select a storage folder first")
            return

        if self.is_running:
            messagebox.showinfo("Info", "Server is already running")
            return

        try:
            port = int(self.port_entry.get())
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('', port))
            self.server_socket.listen(5)
            self.is_running = True

            self.start_button.config(state='disabled')
            self.log_message(f"Server started on port {port}")

            # Start accepting clients in a separate thread
            threading.Thread(target=self.accept_clients, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.log_message(f"Error: {str(e)}")

    def accept_clients(self):
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
                self.log_message(f"New connection from {address}")
            except Exception as e:
                if self.is_running:
                    self.log_message(f"Error accepting client: {str(e)}")

    def handle_client(self, client_socket, address):
        try:
            # Receive client name
            client_name = client_socket.recv(1024).decode()
            self.log_message(f"Client {client_name} connected from {address}")

            while True:
                try:
                    # Receive command
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    command = json.loads(data)
                    action = command.get('action')

                    if action == 'upload':
                        self.handle_upload(client_socket, command)
                    elif action == 'list':
                        self.handle_list(client_socket)
                    elif action == 'download':
                        self.handle_download(client_socket, command)
                    elif action == 'delete':
                        self.handle_delete(client_socket, command)

                except json.JSONDecodeError:
                    self.log_message("Invalid command format received")
                    break

        except Exception as e:
            self.log_message(f"Error handling client: {str(e)}")
        finally:
            client_socket.close()
            self.log_message(f"Connection closed for {address}")

    def handle_upload(self, client_socket, command):
        try:
            filename = command['filename']
            if not filename.endswith('.txt'):
                client_socket.send("ERROR".encode())
                return

            # Receive file size
            size = int(client_socket.recv(10).strip())

            # Receive file data
            file_path = os.path.join(self.storage_folder, filename)
            received = 0
            with open(file_path, 'wb') as f:
                while received < size:
                    data = client_socket.recv(min(4096, size - received))
                    if not data:
                        break
                    f.write(data)
                    received += len(data)

            client_socket.send("SUCCESS".encode())
            self.log_message(f"File {filename} uploaded successfully")

        except Exception as e:
            self.log_message(f"Upload error: {str(e)}")
            client_socket.send("ERROR".encode())

    def handle_list(self, client_socket):
        try:
            files = [f for f in os.listdir(self.storage_folder)
                     if f.endswith('.txt') and os.path.isfile(os.path.join(self.storage_folder, f))]
            client_socket.send(json.dumps(files).encode())
            self.log_message("File list sent to client")
        except Exception as e:
            self.log_message(f"List error: {str(e)}")
            client_socket.send(json.dumps([]).encode())

    def handle_download(self, client_socket, command):
        try:
            filename = command['filename']
            file_path = os.path.join(self.storage_folder, filename)

            if not os.path.exists(file_path):
                client_socket.send("ERROR".encode())
                return

            # Send file size
            file_size = os.path.getsize(file_path)
            client_socket.send(str(file_size).encode().ljust(10))

            # Send file data
            with open(file_path, 'rb') as f:
                while data := f.read(4096):
                    client_socket.send(data)

            self.log_message(f"File {filename} downloaded successfully")

        except Exception as e:
            self.log_message(f"Download error: {str(e)}")
            client_socket.send("ERROR".encode())

    def handle_delete(self, client_socket, command):
        try:
            filename = command['filename']
            file_path = os.path.join(self.storage_folder, filename)

            if os.path.exists(file_path):
                os.remove(file_path)
                client_socket.send("SUCCESS".encode())
                self.log_message(f"File {filename} deleted successfully")
            else:
                client_socket.send("ERROR".encode())
                self.log_message(f"File {filename} not found")

        except Exception as e:
            self.log_message(f"Delete error: {str(e)}")
            client_socket.send("ERROR".encode())


def main():
    root = tk.Tk()
    app = FileServerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
