import socket
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import os

class FileClientApp:
    #---------------------------------------------------------------------GUI part-----------------------------------------------
    def __init__(self, master):
        self.master = master
        self.master.title("File Client")

        self.client_socket = None
        self.connected = False

        # GUI setup
        tk.Label(master, text="Client Name:").grid(row=0, column=0)
        self.name_entry = tk.Entry(master)
        self.name_entry.grid(row=0, column=1)

        tk.Label(master, text="Server IP:").grid(row=1, column=0)
        self.ip_entry = tk.Entry(master)
        self.ip_entry.grid(row=1, column=1)

        tk.Label(master, text="Server Port:").grid(row=2, column=0)
        self.port_entry = tk.Entry(master)
        self.port_entry.grid(row=2, column=1)

        self.connect_button = tk.Button(master, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=3, column=0, columnspan=2)

        self.upload_button = tk.Button(master, text="Upload File", command=self.upload_file, state=tk.DISABLED)
        self.upload_button.grid(row=4, column=0, columnspan=2)

        self.list_button = tk.Button(master, text="List Files", command=self.list_files, state=tk.DISABLED)
        self.list_button.grid(row=5, column=0, columnspan=2)

        self.download_button = tk.Button(master, text="Download File", command=self.download_file, state=tk.DISABLED)
        self.download_button.grid(row=6, column=0, columnspan=2)

        self.delete_button = tk.Button(master, text="Delete File", command=self.delete_file, state=tk.DISABLED)
        self.delete_button.grid(row=7, column=0, columnspan=2)

        self.disconnect_button = tk.Button(master, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=8, column=0, columnspan=2)

        self.activity_list = tk.Listbox(master, width=50)
        self.activity_list.grid(row=8, column=0, columnspan=2)

    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip_entry.get(), int(self.port_entry.get())))
            self.client_socket.send(self.name_entry.get().encode())
            response = self.client_socket.recv(1024).decode()
            if "ERROR" in response:
                messagebox.showerror("Connection Error", response)
                return
            self.connected = True
            self.activity_list.insert(tk.END, "Connected to server.")
            self.upload_button.config(state=tk.NORMAL)
            self.list_button.config(state=tk.NORMAL)
            self.download_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def upload_file(self):
        if not self.connected:
            return
        filepath = filedialog.askopenfilename()
        if not filepath:
            return
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        self.client_socket.send(f"UPLOAD {filename}".encode())
        self.client_socket.recv(1024)  # Wait for READY
        self.client_socket.send(str(filesize).encode())
        with open(filepath, "rb") as f:
            while chunk := f.read(4096):
                self.client_socket.sendall(chunk)
        self.activity_list.insert(tk.END, f"Uploaded: {filename}")

    def list_files(self):
        """Sunucudaki mevcut dosyaları istemci GUI'de listeler."""
        if not self.verify_connection():
            return

        try:
            # LIST komutunu gönder
            self.client_socket.send("LIST".encode())

            # Sunucudan dosya listesini al
            file_list = self.client_socket.recv(4096).decode()
            if file_list == "No files available":
                self.activity_list.insert(tk.END, "No files available on the server")
            else:
                self.activity_list.insert(tk.END, "Available files:\n" + file_list)

        except Exception as e:
            messagebox.showerror("List Error", str(e))
            self.activity_list.insert(tk.END, f"Error retrieving file list: {e}")

    def download_file(self):
        """Dosya indirme işlemini yönetir."""
        if not self.connected:
            return

        # İndirilmek istenen dosyanın adını kullanıcıdan al
        filename = simpledialog.askstring("Download File", "Enter filename:")
        if not filename:
            return

        # Dosyayı nereye kaydedeceğini sor
        save_path = filedialog.asksaveasfilename(title="Save Downloaded File As", initialfile=filename)
        if not save_path:
            return

        try:
            # DOWNLOAD komutunu gönder
            self.client_socket.send(f"DOWNLOAD {filename}".encode())

            # Sunucudan dosya boyutunu al
            response = self.client_socket.recv(1024).decode()
            if response == "FILE_NOT_FOUND":
                self.activity_list.insert(tk.END, f"Download failed: File {filename} not found.")
                return

            # Dosya boyutunu doğrula
            filesize = int(response)
            self.client_socket.send("READY".encode())  # Dosyayı almaya hazır olduğumuzu belirt

            # Dosyayı kaydet
            with open(save_path, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = self.client_socket.recv(min(4096, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            self.activity_list.insert(tk.END, f"Downloaded file: {filename} to {save_path}")

        except Exception as e:
            messagebox.showerror("Download Error", str(e))
            self.activity_list.insert(tk.END, f"Error during download: {e}")

    def delete_file(self):
        """Sunucudaki bir dosyayı siler."""
        if not self.verify_connection():
            return

        # Silinmek istenen dosyanın adını kullanıcıdan al
        filename = simpledialog.askstring("Delete File", "Enter the filename to delete:")
        if not filename:
            return

        try:
            # DELETE komutunu gönder
            self.client_socket.send(f"DELETE {filename}".encode())

            # Sunucudan yanıt bekle
            response = self.client_socket.recv(1024).decode()

            # Yanıta göre işlem sonucunu GUI'ye yaz
            if response == "DELETE_SUCCESS":
                self.activity_list.insert(tk.END, f"Deleted file: {filename}")
            elif response == "FILE_NOT_FOUND":
                self.activity_list.insert(tk.END, f"Failed to delete file: {filename} (File not found)")
            else:
                self.activity_list.insert(tk.END, f"Failed to delete file: {filename} (Unknown error)")

        except Exception as e:
            messagebox.showerror("Delete Error", str(e))
            self.activity_list.insert(tk.END, f"Error during file deletion: {e}")

    def disconnect(self):
        if self.connected:
            self.client_socket.send("DISCONNECT".encode())
            self.client_socket.close()
            self.connected = False
            self.activity_list.insert(tk.END, "Disconnected.")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileClientApp(root)
    root.mainloop()
