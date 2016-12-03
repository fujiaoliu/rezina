#!/usr/bin/python


import time
import sys

import os.path
try:
    import urlparse
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn
except ImportError:
    import urllib.parse as urlparse
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
import re


from .urls import urls


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class DelegateHandler(BaseHTTPRequestHandler):

    _patterns = [re.compile(k) for k in urls]
    _root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'www')
    is_py3 = False
    if sys.version_info >= (3,):
        is_py3 = True

    def _match_path(self, path):
        for p in self._patterns:
            result = p.match(path)
            if result and result.group(0) == path:
                try:
                    return p.pattern, result.group(1)
                except IndexError:
                    return p.pattern, None
        return None, None

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)

        resource = self._root_path + parsed_path.path
        if parsed_path.path in('/', '/summary'):
            resource = self._root_path + "/index.html"

        matched_path, subgroup = self._match_path(parsed_path.path)

        if os.path.isfile(resource):
            response = 200
            with open(resource, 'rb') as f:
                data = f.read()
        elif matched_path in urls:
            response = 200
            data = urls[matched_path](parsed_path.query, subgroup,
                                      self.devices_addr).GET()
            if self.is_py3:
                data = bytearray(data, 'utf-8')
        else:
            response = 404
            resource = self._root_path + '/404.html'
            with open(resource, 'rb') as f:
                data = f.read()

        self.send_response(response)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)


def init_webserver(host, port, devices_addr, logger):
    DelegateHandler.devices_addr = devices_addr
    server = ThreadedHTTPServer((host, port), DelegateHandler)
    try:
        server.serve_forever()
    except:
        logger.exception('Http Server Error')


if __name__ == '__main__':
    init_webserver('127.0.0.1', 8090)
