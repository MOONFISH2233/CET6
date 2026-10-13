# -*- coding: utf-8 -*-
"""给 /opt/astock-learn/server.js 的静态文件服务加上 HTTP Range 支持。

为什么：音频（mp3）要能拖动/跳转，必须支持 Range —— 现在的实现是 fs.readFile
整个读完再 200 返回，浏览器拿不到 Content-Range，只能从头放。
线上 Node 只多这一件事；其他行为（目录 index、路径穿越防护、MIME）原样不动。

用法（在服务器上跑）：python3 _patch_server.py /opt/astock-learn/server.js
先备份成 server.js.bak-range，重复跑是幂等的（检测到已有 Accept-Ranges 就跳过）。
"""
import io
import re
import shutil
import sys

NEW = '''async function handleStatic(req, res, pathname) {
  // 目录请求走 index.html；同时挡住 ../ 之类的路径穿越
  let relative = pathname === '/' ? 'index.html' : decodeURIComponent(pathname).replace(/^\\/+/, '');
  // 子目录请求（如 /cet6/）也补 index.html
  if (relative === "" || relative.endsWith("/")) relative += "index.html";
  const target = path.resolve(PUBLIC_DIR, relative);
  if (target !== PUBLIC_DIR && !target.startsWith(PUBLIC_DIR + path.sep)) {
    return sendError(res, 403, '禁止访问');
  }

  const ext = path.extname(target).toLowerCase();
  const type = MIME[ext] || 'application/octet-stream';

  try {
    const stat = await fs.stat(target);

    // ---- HTTP Range：音频/视频拖动进度条、跳时间点全靠它 ----
    const range = req.headers.range;
    if (range) {
      const m = /^bytes=(\\d*)-(\\d*)$/.exec(range.trim());
      if (m) {
        let start = m[1] === '' ? null : parseInt(m[1], 10);
        let end = m[2] === '' ? null : parseInt(m[2], 10);
        if (start === null && end !== null) {          // bytes=-N：最后 N 字节
          start = Math.max(0, stat.size - end);
          end = stat.size - 1;
        }
        if (start === null) start = 0;
        if (end === null || end >= stat.size) end = stat.size - 1;
        if (start <= end && start < stat.size) {
          res.writeHead(206, {
            'Content-Type': type,
            'Content-Length': end - start + 1,
            'Content-Range': `bytes ${start}-${end}/${stat.size}`,
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'no-cache',
          });
          const stream = fs.createReadStream(target, { start, end });
          stream.on('error', () => res.destroy());
          return stream.pipe(res);
        }
        res.writeHead(416, { 'Content-Range': `bytes */${stat.size}` });
        return res.end();
      }
    }

    res.writeHead(200, {
      'Content-Type': type,
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'no-cache',
    });
    const stream = fs.createReadStream(target);
    stream.on('error', () => res.destroy());
    stream.pipe(res);
  } catch {
    sendError(res, 404, `找不到 ${pathname}`);
  }
}'''

OLD_RE = re.compile(r'async function handleStatic\(res, pathname\) \{.*?\n\}\n', re.S)


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else "/opt/astock-learn/server.js"
    src = io.open(p, encoding="utf-8").read()
    if "Accept-Ranges" in src:
        print("已有 Range 支持，跳过")
        return
    m = OLD_RE.search(src)
    if not m:
        print("!! 没找到 handleStatic，可能改过版了，手动看看")
        sys.exit(1)
    shutil.copyfile(p, p + ".bak-range")
    out = src[:m.start()] + NEW + "\n" + src[m.end():]
    # 调用处要带上 req（原来只传了 res, pathname）
    out = out.replace("await handleStatic(res, url.pathname);",
                      "await handleStatic(req, res, url.pathname);")
    # ⚠️ 这文件用的是 `import fs from 'node:fs/promises'`，上面**没有 createReadStream**！
    #    （第一版就是栽在这：fs.createReadStream 是 undefined，一调用就抛，
    #     进程当场退出 → 所有请求挂死。改从 node:fs 单独引一个。）
    if "createReadStream" not in src:
        out = out.replace("import fs from 'node:fs/promises';",
                          "import fs from 'node:fs/promises';\nimport { createReadStream } from 'node:fs';")
        out = out.replace("fs.createReadStream(", "createReadStream(")
    io.open(p, "w", encoding="utf-8").write(out)
    print("已打补丁并备份到 " + p + ".bak-range")
    print("调用处: " + ("OK" if "handleStatic(req, res, url.pathname)" in out else "!! 没改到"))
    print("流式读取: " + ("OK" if "import { createReadStream } from 'node:fs';" in out else "!! 没引到"))


if __name__ == "__main__":
    main()
