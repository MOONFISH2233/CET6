/* 直接单测补丁后的 handleStatic：不用起服务、不碰路径包含判断，
   只看「Range 怎么响应」「普通请求怎么响应」「路径穿越挡不挡」。
   跑法：node _patch_test.js <补丁后的 server.js 路径> */
const fs = require('fs');
const path = require('path');
const { Writable } = require('stream');

const src = fs.readFileSync(process.argv[2], 'utf8');
const PUB = process.env.PUBDIR || path.join(path.dirname(process.argv[2]), 'public');

// 从 server.js 里抠出要测的两个函数，套一层壳在本地跑
const start = src.indexOf('async function handleStatic');
if (start < 0) { console.log('!! 没找到 handleStatic'); process.exit(1); }
// 从 { 开始做括号配平，取到函数真正结束
const braceStart = src.indexOf('{', start);
let depth = 0, end = -1;
for (let i = braceStart; i < src.length; i++) {
  const c = src[i];
  if (c === '{') depth++;
  else if (c === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
}
if (end < 0) { console.log('!! 函数没配平'); process.exit(1); }
let body = src.slice(start, end);

const mime = {};
for (const m of src.matchAll(/'(\.[a-z0-9]+)':\s*'([^']+)'/g)) mime[m[1]] = m[2];

const code = `
const fs = require('node:fs/promises');
const { createReadStream } = require('node:fs');
const path = require('node:path');
const PUBLIC_DIR = ${JSON.stringify(PUB)};
const MIME = ${JSON.stringify(mime)};
function sendError(res, code, msg) { res.writeHead(code, {'Content-Type': 'application/json'}); res.end(JSON.stringify({error: msg})); }
${body}
module.exports = handleStatic;
`;
const modFile = path.join(require('os').tmpdir(), '_hs_' + Date.now() + '.js');
fs.writeFileSync(modFile, code);
const handleStatic = require(modFile);

function fakeRes() {
  const chunks = [];
  const w = new Writable({ write(c, e, cb) { chunks.push(c); cb(); } });
  w.statusCode = 0; w.headers = {};
  w.writeHead = (code, h) => { w.statusCode = code; w.headers = h || {}; };
  w.on('finish', () => { w.done = Buffer.concat(chunks); });
  return w;
}

const wait = w => new Promise(r => { if (w.writableEnded) return r(); w.on('finish', r); setTimeout(r, 3000); });
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const mp3 = path.join(PUB, 'audio', '2024-06-1.mp3');
  const size = fs.statSync(mp3).size;
  console.log('测试文件 ' + size + ' 字节');

  // 1) 普通 GET
  let res = fakeRes();
  await handleStatic({ headers: {} }, res, '/audio/2024-06-1.mp3');
  await wait(res);
  ck('普通 GET 返回 200', res.statusCode === 200, String(res.statusCode));
  ck('带 Content-Length', res.headers['Content-Length'] === size, String(res.headers['Content-Length']));
  ck('带 Accept-Ranges: bytes', res.headers['Accept-Ranges'] === 'bytes', res.headers['Accept-Ranges']);
  ck('内容长度对', res.done.length === size, String(res.done && res.done.length));

  // 2) 头部 Range
  res = fakeRes();
  await handleStatic({ headers: { range: 'bytes=0-1023' } }, res, '/audio/2024-06-1.mp3');
  await wait(res);
  ck('Range 返回 206', res.statusCode === 206, String(res.statusCode));
  ck('Content-Range 对', res.headers['Content-Range'] === `bytes 0-1023/${size}`, res.headers['Content-Range']);
  ck('只回 1024 字节', res.done.length === 1024, String(res.done && res.done.length));

  // 3) 中段 Range（跳转到 8 分钟处就是这个场景）
  res = fakeRes();
  await handleStatic({ headers: { range: 'bytes=3000000-3001023' } }, res, '/audio/2024-06-1.mp3');
  await wait(res);
  ck('中段 206', res.statusCode === 206, String(res.statusCode));
  ck('中段 Content-Range 对', res.headers['Content-Range'] === `bytes 3000000-3001023/${size}`, res.headers['Content-Range']);
  ck('中段字节对得上', res.done.length === 1024, String(res.done && res.done.length));
  // 校验确实是文件里那一段，不是从头给的
  const whole = fs.readFileSync(mp3);
  ck('内容真的是那一段', Buffer.compare(res.done, whole.slice(3000000, 3001024)) === 0);

  // 4) 尾部 Range
  res = fakeRes();
  await handleStatic({ headers: { range: 'bytes=-512' } }, res, '/audio/2024-06-1.mp3');
  await wait(res);
  ck('bytes=-512 → 206 + 512 字节', res.statusCode === 206 && res.done.length === 512,
     res.statusCode + '/' + (res.done && res.done.length));

  // 5) 越界 Range → 416
  res = fakeRes();
  await handleStatic({ headers: { range: 'bytes=99999999-' } }, res, '/audio/2024-06-1.mp3');
  await wait(res);
  ck('越界返回 416', res.statusCode === 416, String(res.statusCode));

  // 6) 目录 → index.html
  res = fakeRes();
  await handleStatic({ headers: {} }, res, '/');
  await wait(res);
  ck('根路径给 index.html', res.statusCode === 200 && res.done.length > 100, String(res.statusCode));

  // 7) 路径穿越还是挡着
  res = fakeRes();
  await handleStatic({ headers: {} }, res, '/../../etc/passwd');
  await wait(res);
  ck('路径穿越仍被挡（403/404）', res.statusCode === 403 || res.statusCode === 404, String(res.statusCode));

  // 8) 不存在的文件还是 404
  res = fakeRes();
  await handleStatic({ headers: {} }, res, '/audio/nope.mp3');
  await wait(res);
  ck('不存在的文件 404', res.statusCode === 404, String(res.statusCode));

  fs.unlinkSync(modFile);
  console.log(fails ? '!!! ' + fails + ' 项未通过' : 'Range 补丁：全部通过');
  process.exit(fails ? 1 : 0);
})();
