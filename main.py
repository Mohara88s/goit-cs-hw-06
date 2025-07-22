import mimetypes
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from multiprocessing import Process
import logging
from datetime import datetime


uri = "mongodb://mongodb:27017"

HTTPServer_IP = '127.0.0.1'
HTTPServer_PORT = 3000

UDP_IP='127.0.0.1'
UDP_PORT = 5000


def send_data_to_socket(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = UDP_IP, UDP_PORT
    sock.connect(server)
    sock.send(data)


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(data)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('./front/index.html')
        elif pr_url.path == '/message':
            self.send_html_file('./front/message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('./front/error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (HTTPServer_IP, HTTPServer_PORT)
    http = server_class(server_address, handler_class)
    try:
        logging.info(f'HTTPServer started at http://{HTTPServer_IP}:{HTTPServer_PORT}/')
        print(f'HTTPServer started at http://{HTTPServer_IP}:{HTTPServer_PORT}/')
        http.serve_forever()
    except Exception as e:
        http.server_close()
        logging.error(f"{e}")


def save_data(data):
    with MongoClient(uri, server_api=ServerApi('1')) as client:
        db = client.book

        data_parse = urllib.parse.unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        document = {
            "date": str(datetime.now()),
            "username": data_dict["username"],
            "message": data_dict["message"]
        }
        # print(document)
        result = db.cats.insert_one(document)
        logging.info(result)

    
def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = UDP_IP, UDP_PORT
    sock.bind(server)
    logging.info(f'Socket Server started at {UDP_IP}:{UDP_PORT}')
    try:
        while True:
            data, address = sock.recvfrom(1024)
            save_data(data)
    except KeyboardInterrupt as e:
        logging.error(f"{e}")
    finally:
        sock.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(processName)s %(message)s')

    http_server_process = Process(target=run_http_server)
    http_server_process.start()

    socket_server_process = Process(target=run_socket_server)
    socket_server_process.start()