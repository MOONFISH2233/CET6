/* 点词弹窗的排布：短词一行、长词分两行（单词一行，音标/等级下一行），词义单独一段 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

async function openWord(p, word) {
  return p.evaluate(async (w) => {
    const el = [].slice.call(document.querySelectorAll('.w'))
      .filter(x => x.dataset.w === w)[0];
    if (!el) return { err: '文章里没找到 ' + w };
    el.click();
    await new Promise(r => setTimeout(r, 500));
    const pop = document.querySelector('.wpop');
    if (!pop || pop.hidden) return { err: '弹窗没出来' };
    const head = pop.querySelector('.wpop-head');
    const wordEl = pop.querySelector('.wpop-word');
    const phon = pop.querySelector('.wpop-phon');
    const cefr = pop.querySelector('.wpop-cefr');
    const gloss = pop.querySelector('.wpop-gloss');
    const box = e => e ? e.getBoundingClientRect() : null;
    const hb = box(head), wb = box(wordEl), pb = box(phon), cb = box(cefr), gb = box(gloss);
    return {
      word: wordEl.textContent,
      headW: Math.round(hb.width), headH: Math.round(hb.height),
      wordLines: Math.round(wb.height / parseFloat(getComputedStyle(wordEl).lineHeight || 25)),
      wordTop: Math.round(wb.top), wordRight: Math.round(wb.right),
      phonTop: pb ? Math.round(pb.top) : null,
      cefrTop: cb ? Math.round(cb.top) : null,
      glossTop: gb ? Math.round(gb.top) : null,
      headLeft: Math.round(hb.left), headRight: Math.round(hb.right),
      winW: window.innerWidth,
      overflow: hb.right > window.innerWidth || hb.left < 0,
    };
  }, word);
}

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto(BASE + '/p/2024-12-2/reading1.html?v=' + Date.now(), { waitUntil: 'networkidle' });
  await p.waitForTimeout(900);

  // 找文章里最短和最长的一个词
  const picks = await p.evaluate(() => {
    const ws = [].slice.call(document.querySelectorAll('.w')).map(e => e.dataset.w);
    const uniq = [...new Set(ws)];
    uniq.sort((a, b) => a.length - b.length);
    return { short: uniq[0], long: uniq[uniq.length - 1] };
  });
  console.log('  候选: 短=' + picks.short + ' 长=' + picks.long);

  console.log('== 短词 ==');
  const s = await openWord(p, picks.short);
  console.log('  ' + JSON.stringify(s));
  ck('短词弹窗正常', !s.err, JSON.stringify(s));
  if (!s.err) {
    ck('短词：单词一行', s.wordLines <= 1, String(s.wordLines));
    ck('短词：音标和单词同一行', s.phonTop === null || Math.abs(s.phonTop - s.wordTop) < 30,
       s.wordTop + ' vs ' + s.phonTop);
    ck('不溢出屏幕', !s.overflow, JSON.stringify(s));
  }

  console.log('== 长词 ==');
  const l = await openWord(p, picks.long);
  console.log('  ' + JSON.stringify(l));
  ck('长词弹窗正常', !l.err, JSON.stringify(l));
  if (!l.err) {
    ck('长词：单词没有被切成好几段（≤2 行）', l.wordLines <= 2, String(l.wordLines));
    ck('长词：头一行高度容得下两行内容', l.headH >= 20, String(l.headH));
    ck('长词：音标在单词的下一行（或同一行但不重叠）', l.phonTop === null || l.phonTop >= l.wordTop,
       l.wordTop + ' vs ' + l.phonTop);
    ck('不溢出屏幕', !l.overflow, JSON.stringify(l));
    ck('词义在单词下面', l.glossTop === null || l.glossTop >= l.wordTop + 10,
       l.wordTop + ' vs ' + l.glossTop);
  }
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/popup-long.png' });

  console.log('== 三档主题下都不溢出 ==');
  for (const th of ['dark', 'oled']) {
    await p.evaluate(t => { document.documentElement.dataset.theme = t; }, th);
    await p.waitForTimeout(200);
    const r = await openWord(p, picks.long);
    ck(th + ' 档长词不溢出', !r.err && !r.overflow, JSON.stringify(r));
  }

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '点词弹窗：全部通过');
  process.exit(fails ? 1 : 0);
})();
