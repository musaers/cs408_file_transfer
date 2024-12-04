import socket
import threading
import os
import tkinter as tk
from tkinter import filedialog, messagebox


class FileServerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("File Server")

        # GUI elemanları
        tk.Label(master, text="Port:").grid(row=0, column=0)
        self.port_entry = tk.Entry(master)
        self.port_entry.grid(row=0, column=1)

        self.browse_button = tk.Button(master, text="Browse Storage Folder", command=self.browse_folder)
        self.browse_button.grid(row=1, column=0, columnspan=2)

        self.start_button = tk.Button(master, text="Start Server", command=self.start_server)
        self.start_button.grid(row=2, column=0, columnspan=2)

        self.activity_list = tk.Listbox(master, width=80)
        self.activity_list.grid(row=3, column=0, columnspan=2)

        self.storage_folder = ""
        self.server_socket = None
        self.clients = {}  # İstemci bağlantılarını takip eder
        self.files = {}  # {filename: owner}
        self.lock = threading.Lock()  # Thread güvenliği için

    def browse_folder(self):
        """Kullanıcıdan dosya depolama klasörünü seçmesini ister."""
        self.storage_folder = filedialog.askdirectory()
        self.activity_list.insert(tk.END, f"Storage folder set to: {self.storage_folder}")

    def start_server(self):
        """Sunucuyu başlatır ve istemci bağlantılarını kabul etmeye hazır hale getirir."""
        try:
            port = int(self.port_entry.get())
            if not self.storage_folder:
                messagebox.showerror("Error", "Please set the storage folder")
                return

            # Sunucu soketini başlatma
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)

            self.activity_list.insert(tk.END, f"Server started on port {port}")
            self.activity_list.insert(tk.END, f"Storage folder: {self.storage_folder}")

            # İstemcileri kabul etmek için yeni bir thread başlat
            threading.Thread(target=self.accept_clients, daemon=True).start()

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error starting server: {e}")

    def accept_clients(self):
        """İstemci bağlantılarını kabul eder."""
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True).start()
            except Exception as e:
                self.activity_list.insert(tk.END, f"Error accepting client: {e}")
                break

    def handle_client(self, client_socket, client_address):
        """Her istemci için işlemleri yönetir."""
        try:
            # İstemci adını al
            client_name = client_socket.recv(1024).decode()
            if not client_name:
                client_socket.send("ERROR: Invalid client name".encode())
                client_socket.close()
                return

            with self.lock:
                if client_name in self.clients:
                    client_socket.send("ERROR: Client name already in use".encode())
                    client_socket.close()
                    return
                self.clients[client_name] = client_socket

            self.activity_list.insert(tk.END, f"{client_name} connected from {client_address}")
            client_socket.send("WELCOME".encode())

            while True:
                command = client_socket.recv(1024).decode()
                if not command:
                    break

                if command.startswith("UPLOAD"):
                    self.handle_upload(client_socket, client_name, command)
                elif command.startswith("LIST"):
                    self.handle_list(client_socket)
                elif command.startswith("DOWNLOAD"):
                    self.handle_download(client_socket, command)
                elif command.startswith("DELETE"):
                    self.handle_delete(client_socket, client_name, command)
                elif command == "DISCONNECT":
                    break

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error with client {client_address}: {e}")
        finally:
            client_socket.close()
            with self.lock:
                if client_name in self.clients:
                    del self.clients[client_name]
            self.activity_list.insert(tk.END, f"{client_name} disconnected")

    def handle_upload(self, client_socket, client_name, command):
        """Dosya yükleme işlemini yönetir."""
        try:
            _, filename = command.split()
            filepath = os.path.join(self.storage_folder, f"{client_name}_{filename}")
            filesize = int(client_socket.recv(1024).decode())
            client_socket.send("READY".encode())

            with open(filepath, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = client_socket.recv(min(4096, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            with self.lock:
                self.files[f"{client_name}_{filename}"] = client_name
            self.activity_list.insert(tk.END, f"{client_name} uploaded {filename}")
            client_socket.send("UPLOAD_SUCCESS".encode())

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error during upload: {e}")
            client_socket.send(f"UPLOAD_FAILED: {e}".encode())

    def handle_list(self, client_socket):
        """Sunucudaki mevcut dosyaları listeler."""
        try:
            # Mevcut dosyaların listesini oluştur
            with self.lock:
                if not self.files:
                    file_list = "No files available"
                else:
                    file_list = "\n".join([f"{filename} (owner: {owner})" for filename, owner in self.files.items()])

            # Listeyi istemciye gönder
            client_socket.send(file_list.encode())
            self.activity_list.insert(tk.END, "Sent file list to client")

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error sending file list: {e}")
            client_socket.send(f"LIST_FAILED: {e}".encode())

    def handle_download(self, client_socket, command):
        """Dosya indirme işlemini yönetir."""
        try:
            _, filename = command.split()
            filepath = os.path.join(self.storage_folder, filename)

            # Dosyanın varlığını kontrol et
            if not os.path.exists(filepath):
                client_socket.send("FILE_NOT_FOUND".encode())
                self.activity_list.insert(tk.END, f"File not found: {filename}")
                return

            # Dosya boyutunu gönder
            filesize = os.path.getsize(filepath)
            client_socket.send(str(filesize).encode())

            # İstemciden READY bekle
            ready = client_socket.recv(1024).decode()
            if ready != "READY":
                self.activity_list.insert(tk.END, f"Client not ready to receive file: {filename}")
                return

            # Dosya içeriğini gönder
            with open(filepath, "rb") as f:
                while chunk := f.read(4096):  # 4096 byte'lık parçalara bölerek gönder
                    client_socket.sendall(chunk)

            self.activity_list.insert(tk.END, f"File {filename} sent successfully")

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error during download: {e}")
            client_socket.send(f"DOWNLOAD_FAILED: {e}".encode())

    def handle_delete(self, client_socket, client_name, command):
        """Dosya silme işlemini yönetir."""
        try:
            _, filename = command.split()
            filepath = os.path.join(self.storage_folder, f"{client_name}_{filename}")
            if not os.path.exists(filepath):
                client_socket.send("FILE_NOT_FOUND".encode())
                self.activity_list.insert(tk.END, f"Failed to delete: {filename} (File not found)")
                return

            os.remove(filepath)
            with self.lock:
                del self.files[f"{client_name}_{filename}"]
            client_socket.send("DELETE_SUCCESS".encode())
            self.activity_list.insert(tk.END, f"{client_name} deleted {filename}")

        except Exception as e:
            self.activity_list.insert(tk.END, f"Error during delete: {e}")
            client_socket.send(f"DELETE_FAILED: {e}".encode())


if __name__ == "__main__":
    root = tk.Tk()
    app = FileServerApp(root)
    root.mainloop()
