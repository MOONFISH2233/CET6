/* 听力页播放器的实测（390×780）：
   播放器能加载音频吗、能不能跳时间、「听这题」对不对得上、三档主题下样式对不对 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
const SET = '2024-06-1';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 140)); });

  const mediaReqs = [];
  p.on('request', r => { if (/\.mp3(\?|$)/i.test(r.url())) mediaReqs.push(r.url()); });

  console.log('== 打开听力页 ==');
  await p.goto(BASE + '/p/' + SET + '/listening.html?v=' + Date.now(), { waitUntil: 'networkidle' });
  await p.waitForTimeout(1200);

  const st = await p.evaluate(() => {
    const a = document.getElementById('audPlayer');
    return {
      hasCard: !!document.getElementById('audCard'),
      src: a ? a.getAttribute('src') : null,
      preload: a ? a.preload : null,
      playsinline: a ? a.hasAttribute('playsinline') : null,
      x5: a ? a.getAttribute('x5-playsinline') : null,
      chips: document.querySelectorAll('.aud-chip').length,
      qbtns: document.querySelectorAll('.aud-q').length,
      dur: a ? a.duration : null,
      readyState: a ? a.readyState : null,
    };
  });
  console.log('  ' + JSON.stringify(st));
  ck('播放器卡片在', st.hasCard);
  ck('音频指向本套 mp3', st.src === '../../audio/' + SET + '.mp3', st.src);
  ck('preload=none（不点不下载）', st.preload === 'none', st.preload);
  ck('带 playsinline / x5-playsinline', st.playsinline && st.x5 === 'true');
  ck('7 个篇目胶囊', st.chips === 7, String(st.chips));
  ck('25 个「听这题」', st.qbtns === 25, String(st.qbtns));
  ck('一开始没有下 mp3', mediaReqs.length === 0, JSON.stringify(mediaReqs));

  console.log('\n== 能不能真的加载音频 ==');
  const loaded = await p.evaluate(() => new Promise(res => {
    const a = document.getElementById('audPlayer');
    let done = false;
    const fin = (ok, why) => { if (done) return; done = true; res({ ok, why, dur: a.duration, rs: a.readyState }); };
    a.addEventListener('loadedmetadata', () => fin(true, 'loadedmetadata'));
    a.addEventListener('error', () => fin(false, 'error: ' + (a.error && a.error.code)));
    setTimeout(() => fin(a.readyState >= 1, 'timeout rs=' + a.readyState), 15000);
    a.load();
  }));
  console.log('  ' + JSON.stringify(loaded));
  ck('音频元数据加载成功（能播）', loaded.ok, JSON.stringify(loaded));
  if (loaded.ok) ck('时长约 27 分钟', loaded.dur > 1500 && loaded.dur < 1800, String(loaded.dur));

  console.log('\n== 点「跳到第 3 篇」==');
  const chipT = await p.locator('.aud-chip').nth(2).getAttribute('data-aud');
  await p.locator('.aud-chip').nth(2).click();
  await p.waitForTimeout(1200);
  const afterChip = await p.evaluate(() => ({ t: document.getElementById('audPlayer').currentTime,
                                              hash: location.hash, paused: document.getElementById('audPlayer').paused }));
  console.log('  目标 ' + chipT + 's → 实际 ' + afterChip.t.toFixed(1) + 's · hash=' + afterChip.hash);
  ck('跳到了那片的位置', Math.abs(afterChip.t - parseFloat(chipT)) < 3, JSON.stringify(afterChip));
  ck('地址里带上了时间点', /t=[\d.]+/.test(afterChip.hash), afterChip.hash);

  console.log('\n== 点某题的「听这题」==');
  const btn = p.locator('.aud-q').nth(13);          // 找一道靠后的题
  const bt = await btn.getAttribute('data-aud');
  const qno = await btn.evaluate(e => e.closest('.q').dataset.qno);
  await btn.click();
  await p.waitForTimeout(1200);
  const afterQ = await p.evaluate(() => ({ t: document.getElementById('audPlayer').currentTime,
                                           hash: location.hash }));
  console.log('  第 ' + qno + ' 题 → ' + bt + 's → 实际 ' + afterQ.t.toFixed(1) + 's');
  ck('跳到这道题的位置', Math.abs(afterQ.t - parseFloat(bt)) < 3, JSON.stringify(afterQ));

  console.log('\n== 带 #t= 直接打开（分享/刷新场景）==');
  await p.goto(BASE + '/p/' + SET + '/listening.html?x=1#t=900', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2500);
  const afterHash = await p.evaluate(() => ({ t: document.getElementById('audPlayer').currentTime,
                                              rs: document.getElementById('audPlayer').readyState }));
  console.log('  #t=900 → 实际 ' + afterHash.t.toFixed(1) + 's');
  ck('打开就跳到该时间点', Math.abs(afterHash.t - 900) < 5, JSON.stringify(afterHash));

  console.log('\n== 三档主题 ==');
  for (const th of ['light', 'dark', 'oled']) {
    await p.evaluate(t => { document.documentElement.dataset.theme = t; localStorage.setItem('cet6-theme', t); }, th);
    await p.waitForTimeout(250);
    const m = await p.evaluate(() => {
      const de = document.documentElement;
      const over = [];
      document.querySelectorAll('.wrap *').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.width && (r.left < -1 || r.right > window.innerWidth + 1)) over.push((e.className || e.tagName) + ' ' + Math.round(r.left) + '→' + Math.round(r.right));
      });
      const chip = document.querySelector('.aud-chip');
      const q = document.querySelector('.aud-q');
      const card = document.getElementById('audCard');
      return { h: de.scrollWidth > de.clientWidth, over: over.slice(0, 3),
               cardBg: getComputedStyle(card).backgroundColor,
               chipBg: getComputedStyle(chip).backgroundColor,
               chipFg: getComputedStyle(chip).color,
               audioH: Math.round(document.getElementById('audPlayer').getBoundingClientRect().height),
               chipH: Math.round(chip.getBoundingClientRect().height),
               qH: Math.round(q.getBoundingClientRect().height) };
    });
    console.log('  [' + th + '] 卡片' + m.cardBg + ' 胶囊' + m.chipBg + '/' + m.chipFg +
                ' 播放器高' + m.audioH + ' 胶囊高' + m.chipH + ' 听这题高' + m.qH +
                ' 溢出=' + m.h);
    ck(th + ' 无横向溢出', !m.h);
    ck(th + ' 无元素出界', m.over.length === 0, JSON.stringify(m.over));
    ck(th + ' 胶囊够大好点（≥32px）', m.chipH >= 32, String(m.chipH));
  }
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/audio-listening.png' });

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '听力播放器：全部通过');
  process.exit(fails ? 1 : 0);
})();
