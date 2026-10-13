# -*- coding: utf-8 -*-
"""
本地预览用的静态服务器。

比 `python -m http.server` 多的就一件事：**支持 HTTP Range**。
音频（mp3）必须有 Range 才能拖动/跳转 —— 没有的话浏览器跳不动，
只能从头播（线上是 nginx，自带 Range，不用管）。

用法：python _serve.py [端口] [目录]
"""
import functools
import http.server
import os
import socketserver
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 关键：告诉浏览器「可以按字节范围取」，audio 才能 seek
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):      # 别刷屏
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    root = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "site")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", port),
                                         functools.partial(Handler, directory=root)) as httpd:
        print("serving %s at http://127.0.0.1:%d/  (Range 支持)" % (root, port))
        httpd.serve_forever()


if __name__ == "__main__":
    main()
