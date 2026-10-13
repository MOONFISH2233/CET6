/* 线上音频实测：能加载吗、能跳到中段吗、点「听这题」真的跳吗 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://47.109.130.65:5173/cet6';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 120)); });

  console.log('== 打开线上听力页 ==');
  await p.goto(BASE + '/p/2024-06-1/listening.html', { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(1500);
  const head = await p.evaluate(() => {
    const a = document.getElementById('audPlayer');
    return { src: a.getAttribute('src'), preload: a.preload,
             chips: document.querySelectorAll('.aud-chip').length,
             qs: document.querySelectorAll('.aud-q').length };
  });
  console.log('  ' + JSON.stringify(head));
  ck('播放器在', !!head.src);
  ck('7 篇胶囊 + 25 个听这题', head.chips === 7 && head.qs === 25, JSON.stringify(head));

  console.log('== 真的加载音频（线上要支持 Range）==');
  const meta = await p.evaluate(() => new Promise(res => {
    const a = document.getElementById('audPlayer');
    let done = false;
    const fin = (ok, why) => { if (done) return; done = true; res({ ok, why, dur: a.duration }); };
    a.addEventListener('loadedmetadata', () => fin(true, 'ok'));
    a.addEventListener('error', () => fin(false, 'error ' + (a.error && a.error.code)));
    setTimeout(() => fin(a.readyState >= 1, 'timeout rs=' + a.readyState), 20000);
    a.load();
  }));
  console.log('  ' + JSON.stringify(meta));
  ck('线上音频能加载', meta.ok, JSON.stringify(meta));
  ck('时长约 27 分钟', meta.dur > 1500 && meta.dur < 1800, String(meta.dur));

  console.log('== 跳到中段（要 Range 才能秒跳）==');
  const t0 = Date.now();
  const seekRes = await p.evaluate(() => new Promise(res => {
    const a = document.getElementById('audPlayer');
    a.currentTime = 900;
    const start = Date.now();
    const check = () => {
      if (Math.abs(a.currentTime - 900) < 6) return res({ ok: true, t: a.currentTime, ms: Date.now() - start });
      if (Date.now() - start > 12000) return res({ ok: false, t: a.currentTime });
      setTimeout(check, 200);
    };
    check();
  }));
  console.log('  跳到 900s → ' + seekRes.t.toFixed(1) + 's（' + (seekRes.ms || 0) + 'ms）');
  ck('能跳到录音中段', seekRes.ok, JSON.stringify(seekRes));

  console.log('== 点「听这题」（线上）==');
  const btn = p.locator('.aud-q').nth(6);
  const bt = await btn.getAttribute('data-aud');
  await btn.click();
  await p.waitForTimeout(2500);
  const after = await p.evaluate(() => ({ t: document.getElementById('audPlayer').currentTime, hash: location.hash }));
  console.log('  ' + bt + 's → ' + after.t.toFixed(1) + 's · hash=' + after.hash);
  ck('线上点听这题能跳', Math.abs(after.t - parseFloat(bt)) < 6, JSON.stringify(after));

  console.log('== 打卡站今日卡片 ==');
  await p.goto(BASE + '/plan/index.html', { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(1500);
  const plan = await p.evaluate(() => {
    const a = document.querySelector('#todayCard .aud-embed audio');
    return a ? { src: a.getAttribute('src'), preload: a.preload } : null;
  });
  console.log('  ' + JSON.stringify(plan));
  if (plan) {
    ck('今日卡片有播放器且 preload=none', plan.preload === 'none', JSON.stringify(plan));
    const ok = await p.evaluate(() => new Promise(res => {
      const a = document.querySelector('#todayCard .aud-embed audio');
      let done = false;
      const fin = v => { if (!done) { done = true; res(v); } };
      a.addEventListener('loadedmetadata', () => fin({ ok: true, dur: a.duration }));
      a.addEventListener('error', () => fin({ ok: false, code: a.error && a.error.code }));
      setTimeout(() => fin({ ok: a.readyState >= 1 }), 20000);
      a.load();
    }));
    console.log('  ' + JSON.stringify(ok));
    ck('打卡站的播放器也能加载', ok.ok, JSON.stringify(ok));
  } else {
    console.log('  （今天没有听力任务，跳过）');
  }

  await p.screenshot({ path: 'D:/学习/六级/build/_shots/audio-live.png' });
  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '线上音频：全部通过');
  process.exit(fails ? 1 : 0);
})();
