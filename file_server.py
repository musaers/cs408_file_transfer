import socket
import threading
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk



class FileServerApp:
    def __init__(self, master):
        # Initialize GUI and  the other server variables
        self.master = master
        self.master.title("File Server")
        self.master.geometry("600x500")

        # Server  UI
        config_frame = ttk.LabelFrame(master, text="Server Configuration")
        config_frame.pack(padx=10, pady=5, fill="x")

        # Input server port
        ttk.Label(config_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame)

        self.port_entry.grid(row=0, column=1, padx=5, pady=5)

        # Folder selection
        ttk.Label(config_frame, text="Folder:").grid(row=1, column=0, padx=5, pady=5)
        self.folder_label = ttk.Label(config_frame, text="No folder selected")
        self.folder_label.grid(row=1, column=1, padx=5, pady=5)

        self.browse_button = ttk.Button(config_frame, text="Browse", command=self.browse_folder)
        self.browse_button.grid(row=1, column=2, padx=5, pady=5)

        # Button to start
        self.start_button = ttk.Button(config_frame, text="Start Server", command=self.start_server)
        self.start_button.grid(row=2, column=0, columnspan=3, pady=10)

        #display for server activity
        log_frame = ttk.LabelFrame(master, text="Server Log")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=20)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

        # Initialize server variables
        self.server_socket = None
        self.storage_folder = ""  # storeage folder
        self.is_running = False  # running status of server

    def log_message(self, message):
        # Helper function to add mesages to the log displaying
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def browse_folder(self):
        # Open folder selection
        folder = filedialog.askdirectory()
        if folder:
            self.storage_folder = folder
            self.folder_label.config(text=folder)
            self.log_message(f"Storage folder set to: {folder}")

    def start_server(self):
        # Starts the server on the requested port
        if not self.storage_folder:
            messagebox.showerror("Error", "Please select a storage folder first")
            return

        if self.is_running:
            messagebox.showinfo("Info", "Server is already running")
            return

        try:
            # Create, bind server socket
            port = int(self.port_entry.get())
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('', port))
            self.server_socket.listen(5)
            self.is_running = True

            self.start_button.config(state='disabled')  # Disable start button
            self.log_message(f"Server started on port {port}")

            # Start the  client handle threats
            threading.Thread(target=self.accept_clients, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.log_message(f"Error: {str(e)}")

    def accept_clients(self):
        # Accept client connections
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                # Handle each client in a separate thread
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()

            except Exception as e:
                if self.is_running:
                    self.log_message(f"Error accepting client: {str(e)}")

    def handle_client(self, client_socket, address):
        # Handles communication with client
        try:
            client_name = client_socket.recv(1024).decode()  # Get client name
            self.log_message(f"Client {client_name} connected from {address}")

            while True:
                try:
                    # Receive and parse the command which is from client
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    command = json.loads(data)  # Convert to JSON
                    action = command.get('action')

                    # do requested action
                    if action == 'upload':
                        self.handle_upload(client_socket, command, client_name)
                    elif action == 'list':
                        self.handle_list(client_socket, client_name)
                    elif action == 'download':
                        self.handle_download(client_socket, command, client_name)
                    elif action == 'delete':
                        self.handle_delete(client_socket, command, client_name)

                except json.JSONDecodeError:
                    # Handle invalid JSON
                    self.log_message(f"Invalid command format received from client {client_name}")
                    break

        except Exception as e:
            self.log_message(f"Error handling client {client_name}: {str(e)}")

        finally:
            client_socket.close()  # make sure client socket is closed
            self.log_message(f"Connection closed for client [{client_name}] ({address})")

    def handle_upload(self, client_socket, command, client_name):
        # Handle file upload
        try:
            filename = command['filename']
            if not filename.endswith('.txt'):
                client_socket.send("ERROR".encode())
                return

            size = int(client_socket.recv(10).strip())  # get file size
            file_path = os.path.join(self.storage_folder, filename)

            # update storage folder
            received = 0
            with open(file_path, 'wb') as f:
                while received < size:
                    data = client_socket.recv(min(4096, size - received))
                    if not data:
                        break
                    f.write(data)
                    received += len(data)

            client_socket.send("SUCCESS".encode())  # Confirm success
            self.log_message(f"File {filename} uploaded by client [{client_name}]")

        except Exception as e:
            self.log_message(f"Upload error by client [{client_name}]: {str(e)}")
            client_socket.send("ERROR".encode())

    def handle_list(self, client_socket, client_name):
        # Sends the list of files
        try:
            files = [f for f in os.listdir(self.storage_folder) if f.endswith('.txt') and os.path.isfile(os.path.join(self.storage_folder, f))]
            client_socket.send(json.dumps(files).encode())  # Send file list
            self.log_message(f"List of files sent to client [{client_name}]")

        except Exception as e:
            self.log_message(f"List error for client [{client_name}]: {str(e)}")
            client_socket.send(json.dumps([]).encode())

    def handle_download(self, client_socket, command, client_name):
        # handle download requests
        try:
            filename = command['filename']
            file_path = os.path.join(self.storage_folder, filename)

            if not os.path.exists(file_path):  # file exists or not
                client_socket.send("ERROR".encode())
                return

            file_size = os.path.getsize(file_path)  #file size
            client_socket.send(str(file_size).encode().ljust(10))  # Send it

            # Send file data
            with open(file_path, 'rb') as f:
                while data := f.read(4096):
                    client_socket.send(data)

            self.log_message(f"File {filename} downloaded by {client_name}")

        except Exception as e:
            self.log_message(f"Download error by {client_name}: {str(e)}")
            client_socket.send("ERROR".encode())

    def handle_delete(self, client_socket, command, client_name):
        # Handles file deletion requests
        try:
            filename = command['filename']
            file_path = os.path.join(self.storage_folder, filename)

            if os.path.exists(file_path):  # Check if file is there
                os.remove(file_path)  # Delete file
                client_socket.send("SUCCESS".encode())
                self.log_message(f"File {filename} deleted by client [{client_name}]")
            else:
                client_socket.send("ERROR".encode())
                self.log_message(f"File {filename} not found - delete attempted by client [{client_name}]")

        except Exception as e:
            self.log_message(f"Delete error: {str(e)}")
            client_socket.send("ERROR".encode())


def main():

    root = tk.Tk()
    app = FileServerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
