import network
import socket
import time
from secrets import mysecrets
import uasyncio as asyncio

class WebServer:
    def __init__(self):
        self.ip_address = None
        self.server_task = None
        self._current_path = "/"
        
    @property
    def current_path(self):
        """Get the most recent path requested by a client"""
        return self._current_path
        
    def connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(mysecrets['SSID'], mysecrets['key'])
        while wlan.ifconfig()[0] == '0.0.0.0':
            print('.', end=' ')
            time.sleep(1)
        self.ip_address = wlan.ifconfig()[0]
        print(f'Connected - IP: {self.ip_address}')
        return self.ip_address

    async def handle_client(self, client, addr):
        print(f"Handling client from {addr}")
        try:
            client.setblocking(False)
            request = b""
            while True:
                try:
                    chunk = client.recv(1024)
                    if not chunk:
                        break
                    request += chunk
                    if b"\r\n\r\n" in request:
                        break
                except OSError as e:
                    if e.args[0] == 11:
                        await asyncio.sleep(0.1)
                        continue
                    raise
                
            if request:
                request_str = request.decode('utf-8')
                first_line = request_str.split('\n')[0]
                self._current_path = first_line.split(' ')[1]
                print("Path requested:", self._current_path)
                
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>You requested path: {self._current_path}</body></html>"
                client.send(response.encode())
        except Exception as e:
            print("Error handling client:", e)
        finally:
            client.close()
            print(f"Connection closed for {addr}")

    async def serve(self):
        addr = socket.getaddrinfo(self.ip_address, 80)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(5)
        s.setblocking(False)
        print(f"Server listening on http://{addr[0]}:{addr[1]}")
        
        while True:
            try:
                client, addr = s.accept()
                asyncio.create_task(self.handle_client(client, addr))
            except OSError as e:
                if e.args[0] == 11:
                    await asyncio.sleep(0.1)
                    continue
                print("Socket error:", e)

    async def start(self):
        """Start the web server"""
        if not self.ip_address:
            self.connect_wifi()
        self.server_task = asyncio.create_task(self.serve())
        return self.server_task

    def stop(self):
        """Stop the web server"""
        if self.server_task:
            self.server_task.cancel()
            self.server_task = None