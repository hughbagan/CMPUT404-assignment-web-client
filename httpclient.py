#!/usr/bin/env python3
# coding: utf-8
# Copyright 2021 Abram Hindle, https://github.com/tywtyw2002, https://github.com/treedust, and Hugh Bagan
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib.parse
from http import HTTPStatus
import json


def help():
    print("httpclient.py [GET/POST] [URL]\n")


class HTTPResponse(object):
    
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body
    
    def get_codes() -> list: # classmethod?
        """ Returns all possible HTTP status codes. """
        codes = []
        for status in list(HTTPStatus):
            codes.append(status.value)
        return codes


class HTTPClient(object):

    def parse_url(self, url):
        # RichieHindle, BartoszKP https://stackoverflow.com/a/1059596
        url_parts = re.findall(r"[\w\.]+", url)
        colons = re.findall(r"[:]+", url)
        has_scheme, has_port = 0, 0
        if 'http' in url_parts[0]: # scheme specified in url
            has_scheme = 1
        host = url_parts[has_scheme]
        if len(colons) >= 1+has_scheme: # port specified in url
            has_port = 1
        if has_port:
            port = int(url_parts[has_scheme+has_port])
        else:
            port = 80 # Assuming!
        # Assume everything afterward is the path...
        path = '/'
        for i in range(has_scheme+has_port+1, len(url_parts), 1):
            path += url_parts[i]
        # Attempt to reconstruct the path ending (I suck at regex)
        if len(path) > 2:
            path = url[url.find(host)+len(host)+(has_port*(len(str(port))+1)):]
        return (host, port, path)

    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_ip = socket.gethostbyname(host) # get host info first
        self.socket.connect((remote_ip, port))
        return remote_ip
    
    def get_code(self, data):
        # Should probably use regex here, but I'm lazy.
        headers = data.split('\n')
        code = 500
        for c in HTTPResponse.get_codes():
            if str(c) in headers[0]:
                code = c
                break
        return code

    def get_headers(self,data):
        return data.split('\r\n\r\n')[0]

    def get_body(self, data):
        return data.split('\r\n\r\n')[1] # NOTE could error?
    
    def sendall(self, data):
        # Is urllib.parse really needed?
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close() 

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
            else:
                done = not part
        return buffer.decode('utf-8')

    def GET(self, url, args=None):
        """ Does not follow 3XX redirects! Ignores args. """
        host, port, path = self.parse_url(url)
        #print("host:", host, "port:", port, "path:", path)
        request = f'GET {path} HTTP/1.1\r\n'\
                + f'Host: {host}\r\n'\
                + f'User-Agent: customhttpclient\r\n'\
                + f'Connection: close\r\n'\
                + f'\r\n' # Maybe need Accept header?
        remote_ip = self.connect(host, port)
        print(f'Socket connected to {host}:{port} on IP {remote_ip}')
        self.sendall(request)
        print(f'Request sent:\n{request}')
        self.socket.shutdown(socket.SHUT_WR)
        received = self.recvall(self.socket)
        print('Received response:')
        print(self.get_headers(received))
        code = self.get_code(received)
        body = self.get_body(received)
        print(f'\n{body}')
        self.close()
        return HTTPResponse(code, body)

    def POST(self, url, args=None):
        """ Assumes args are content body. """
        host, port, path = self.parse_url(url)        
        # Dump all of the args into the POST content
        content = f''
        if args:
            items = list(args.items())
            for i in range(len(items)):
                item = items[i]
                content += f'{item[0]}' + f'=' + f'{item[1]}'
                if i < len(items)-1:
                    content += f'&'
        content_length = len(content) #sys.getsizeof(bytes(content,'utf-8'))
        request = f'POST {path} HTTP/1.1\r\n'\
                + f'Host: {host}\r\n'\
                + f'User-Agent: customhttpclient\r\n'\
                + f'Content-Type: application/x-www-form-urlencoded\r\n'\
                + f'Content-Length: {content_length}\r\n'\
                + f'Connection: close\r\n'\
                + f'\r\n'\
                + content
        remote_ip = self.connect(host, port)
        print(f'Socket connected to {host}:{port} on IP {remote_ip}')
        self.sendall(request)
        # Request content may not display correctly when print()'d
        print(f'Request sent:\n{request}')
        self.socket.shutdown(socket.SHUT_WR)
        received = self.recvall(self.socket)
        print('Received response:')
        print(self.get_headers(received))
        code = self.get_code(received)
        body = self.get_body(received)
        print(f'\n{body}')
        self.close()
        return HTTPResponse(code, body)

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )


if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) > 3):
        """
        Arguments for POST will be expected as a JSON, and loaded to dict
        Example usage:
        python3 httpclient.py POST https://webdocs.cs.ualberta.ca/~hindle1/1.py '{"a":"aaaaaaaaaaaaa","b":"bbbbbbbbbbbbbbbbbbbbbb","c":"c","d":"012345\r67890\n2321321\n\r"}'
        chander https://stackoverflow.com/a/18006814
        """
        print(sys.argv)
        print(client.command( sys.argv[2], sys.argv[1], json.loads(sys.argv[3])))
    elif (len(sys.argv) == 3):
        print(client.command( sys.argv[2], sys.argv[1] ))
    else:
        print(client.command( sys.argv[1] ))
