import network
import socket
import time
from secrets import mysecrets
import uasyncio as asyncio
import ujson

class WebServer:
    def __init__(self, controller):
        self.ip_address = None
        self.server_task = None
        self._current_path = "/"
        self.controller = controller
        
        
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
    
    def handle_data(self, path, data):        
        content = {}
        
        # handle webpage stuff
        if path == '/':       
            with open('index.html', 'r', encoding='utf-8') as file:
                content = file.read()
            content_type = "text/html"
        elif path == '/style.css':
            # Serve the CSS file
            with open('style.css', 'r', encoding='utf-8') as file:
                content = file.read()
            content_type = "text/css"  
        elif path == '/script.js':
            # Serve the JavaScript file
            with open('script.js', 'r', encoding='utf-8') as file:
                content = file.read()
            content_type = "application/javascript"
            #print(content[-100:])
        else:
            # handle user requests
            if path == '/power':
                cont = self.controller.power_switch(data["power"])
            elif path == '/mode':
                cont = self.controller.mode_switch(data["mode"])
            elif path == '/status':
                cont = self.controller.get_status(data["interval"])
            elif path == '/settings':
                cont = self.controller.get_settings()
            elif path == '/save_settings':
                cont = self.controller.save_settings(data)
            elif path == '/history':
                cont = self.controller.get_history()
            else:
                cont = "this path doesn't exist"
            
            content = ujson.dumps(cont)
            content_type = "application/json"
            
        content_length = len(content.encode('utf-8'))
            
        response = f"HTTP/1.1 200 OK\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {content_length}\r\n"
        response += "Access-Control-Allow-Origin: *\r\n\r\n"
        response += content
        
        return response.encode('utf-8')


    async def handle_client(self, client, addr):
        print(f"Handling client from {addr}")
        try:
            client.setblocking(False)
            request = b""
            headers = {}
            content_length = 0
            
            # Read headers first
            while True:
                try:
                    chunk = client.recv(1024)
                    if not chunk:
                        break
                    request += chunk
                    if b"\r\n\r\n" in request:
                        headers_end = request.find(b"\r\n\r\n")
                        headers_data = request[:headers_end].decode('utf-8')
                        
                        # Parse headers
                        for line in headers_data.split('\r\n')[1:]:  # Skip first line (HTTP method)
                            if ': ' in line:
                                key, value = line.split(': ', 1)
                                headers[key.lower()] = value
                        
                        # Get content length if present
                        content_length = int(headers.get('content-length', 0))
                        break
                        
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN
                        await asyncio.sleep(0.1)
                        continue
                    raise

            # Parse request line
            request_line = request.split(b'\r\n')[0].decode('utf-8')
            method, path, _ = request_line.split(' ')
            self._current_path = path
            
            # Read body if it exists
            body = b""
            body_start = request[request.find(b"\r\n\r\n") + 4:]
            body += body_start
            
            remaining = content_length - len(body)
            while remaining > 0:
                try:
                    chunk = client.recv(min(1024, remaining))
                    if not chunk:
                        break
                    body += chunk
                    remaining -= len(chunk)
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN
                        await asyncio.sleep(0.1)
                        continue
                    raise

            # Debug information
            #print(f"Headers received: {headers}")
            #print(f"Content-Length: {content_length}")
            #print(f"Body length: {len(body)}")
                
            # Get request body if present
            data = None
            if body:
                try:
                    data = ujson.loads(body)  # Parse JSON string into a Python dictionary
                except ValueError as e:
                    print("Error parsing body:", e)
                    print("body: ", body)
                                                    
            response = self.handle_data(path, data)
                
            data_sent = 0
            total_data = len(response)
            
            while data_sent < total_data:
                try:
                    # Send data in smaller chunks (e.g., 1024 bytes)
                    chunk = response[data_sent:data_sent + 1024]
                    bytes_written = client.write(chunk)
                    if bytes_written is None:
                        await asyncio.sleep(0.1)
                        continue
    
                    data_sent += bytes_written
                    
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN
                        # Socket is not ready, retry after a short delay
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        # If the error is not EAGAIN, raise it
                        raise
                except Exception as e:
                    print(f"Error while sending data: {e}")
                    break  # Optionally, break on other errors

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
                if e.args[0] == 11:  # EAGAIN
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