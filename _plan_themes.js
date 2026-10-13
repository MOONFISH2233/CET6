/* 计划页在三档主题下的检查：不横向溢出、字色对比、格子状态可辨 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  await p.goto(BASE + '/plan/index.html?v=' + Date.now());
  await p.waitForTimeout(1000);

  for (const th of ['light', 'dark', 'oled']) {
    await p.evaluate(t => {
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('cet6-theme', t);
    }, th);
    await p.waitForTimeout(250);
    const m = await p.evaluate(() => {
      const de = document.documentElement;
      const over = [];
      document.querySelectorAll('.wrap *').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.width && (r.left < -1 || r.right > window.innerWidth + 1)) {
          over.push((e.className || e.tagName) + ' ' + Math.round(r.left) + '→' + Math.round(r.right));
        }
      });
      const cell = document.querySelector('.wk div');
      const today = document.querySelector('.wk div.today');
      const note = document.querySelector('.dayrow .note');
      const cs = e => e ? getComputedStyle(e) : null;
      return {
        hScroll: de.scrollWidth > de.clientWidth ? de.scrollWidth + '>' + de.clientWidth : 'no',
        over: over.slice(0, 3),
        cellBg: cs(cell).backgroundColor, cellFg: cs(cell).color,
        todayShadow: cs(today).boxShadow, todayFg: cs(today).color,
        noteBg: cs(note).backgroundColor, notePad: cs(note).paddingTop,
        pageH: de.scrollHeight,
      };
    });
    console.log('[' + th + '] 格子 ' + m.cellBg + '/' + m.cellFg + ' · 今天圈 ' + m.todayShadow +
                ' · 提示 底' + m.noteBg + ' pad' + m.notePad + ' · 页高' + m.pageH);
    ck(th + ' 无横向溢出', m.hScroll === 'no', m.hScroll);
    ck(th + ' 无元素出界', m.over.length === 0, JSON.stringify(m.over));
    ck(th + ' 提示不再是黄色警示框', m.noteBg === 'rgba(0, 0, 0, 0)' && m.notePad === '0px',
       m.noteBg + '/' + m.notePad);
    ck(th + ' 今天的格子有圈', /inset/.test(m.todayShadow), m.todayShadow);
  }
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '三档主题：全部通过');
  await b.close();
  process.exit(fails ? 1 : 0);
})();
