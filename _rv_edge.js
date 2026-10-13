/* 边界：生词本为空 / 词查不到释义 / 到期复习口径 / 发音按钮接线 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));

  console.log('== 生词本为空 ==');
  await p.goto(BASE + '/review.html');
  await p.evaluate(() => { localStorage.clear(); });
  await p.reload();
  await p.waitForTimeout(900);
  const s1 = await p.locator('#rvStat').innerText();
  console.log('  ' + s1.replace(/\n/g, ' | '));
  ck('提示今天没有要背的词', /没有要背的词/.test(s1), s1);
  ck('开始按钮被禁用', await p.locator('#rvStartBtn').isDisabled());
  ck('按钮文案变成背完了', /背完了/.test(await p.locator('#rvStartBtn').innerText()));

  // 这两个词核心库和 ECDICT 兜底库都没有（实测过：nebraska 在兜底库里有，不能用）
  console.log('== 词查不到释义（两个词库都没有）==');
  await p.evaluate(() => {
    localStorage.setItem('cet6:vocab', JSON.stringify([
      { w: 'berkson', gloss: '', cefr: '', src: '2023-06-1/reading1', t: Date.now() },
      { w: 'zzqxww', gloss: '', cefr: '', src: '2023-06-1/reading1', t: Date.now() },
    ]));
    localStorage.removeItem('cet6:srs');
  });
  await p.reload();
  await p.waitForTimeout(900);
  console.log('  首页: ' + (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | '));
  await p.click('#rvStartBtn');
  await p.waitForTimeout(700);
  const s2 = await p.locator('#rvStat').innerText();
  console.log('  点开始后: ' + s2.replace(/\n/g, ' | '));
  ck('组不出题时给出说明而不是空卡片', /组不出题/.test(s2), s2);
  ck('会话区没露出来', await p.locator('#rvSession').isHidden());

  console.log('== 到期复习口径 ==');
  await p.evaluate(() => {
    const now = Date.now(), DAY = 86400000;
    const d0 = new Date(); d0.setHours(0, 0, 0, 0);
    const vocab = [
      { w: 'antibiotic', gloss: 'n. 抗生素', cefr: 'B2', src: '2023-06-1/cloze', t: now - 1000 },
      { w: 'hierarchical', gloss: 'adj. 分层的', cefr: 'C1', src: '2023-06-1/cloze', t: now - 2000 },
      { w: 'sustainable', gloss: 'adj. 可持续的', cefr: 'B2', src: '2023-06-1/cloze', t: now - 3000 },
    ];
    localStorage.setItem('cet6:vocab', JSON.stringify(vocab));
    localStorage.setItem('cet6:srs', JSON.stringify({
      // 已到期（昨天）
      antibiotic: { EF: 2.5, I: 1, n: 1, due: d0.getTime() - DAY, seen: 1, ok: 1, bad: 0, t: now },
      // 明天才到期 + n=0（上回答错）→ 按规则「答错明天必来」，今天仍要出现
      hierarchical: { EF: 2.3, I: 1, n: 0, due: d0.getTime() + DAY, seen: 2, ok: 1, bad: 1, t: now },
      // 已学会 → 不再出现
      sustainable: { EF: 2.5, I: 365, n: 9, due: now + 300 * DAY, learned: 1, seen: 9, ok: 9, bad: 0, t: now },
    }));
  });
  await p.reload();
  await p.waitForTimeout(900);
  const s3 = await p.locator('#rvStat').innerText();
  console.log('  ' + s3.replace(/\n/g, ' | '));
  ck('今天只算 2 个（到期的 + 答错要来的）', /今天 2 个词/.test(s3), s3);
  ck('「已学会」的不再排进来', !/今天 3 个/.test(s3));
  const sum2 = await p.locator('#rvHomeNote').innerText();
  console.log('  注: ' + sum2);

  console.log('== 发音接线 ==');
  await p.click('#rvStartBtn');
  await p.waitForTimeout(600);
  const spk = await p.evaluate(() => {
    const b = document.querySelector('#rvSpk .spk');
    return b ? { say: b.dataset.say, cls: b.className, svg: !!b.querySelector('svg') } : null;
  });
  console.log('  喇叭: ' + JSON.stringify(spk));
  ck('喇叭带 data-say（word.js 的委托钩子）', !!spk && spk.say.length > 1, JSON.stringify(spk));
  ck('喇叭用的是背单词页的皮肤', !!spk && /rv-spk-btn/.test(spk.cls), spk && spk.cls);
  ck('喇叭是内联 SVG（不是文字）', !!spk && spk.svg);
  const spoken = await p.evaluate(() => {
    let said = null;
    const ss = window.speechSynthesis;
    const orig = ss.speak.bind(ss);
    ss.speak = u => { said = u.text; };            // 拦截，避免测试环境真的出声
    document.querySelector('#rvSpk .spk').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    ss.speak = orig;
    return said;
  });
  console.log('  点喇叭后朗读: ' + spoken);
  ck('点喇叭会朗读当前这个词', !!spoken && spoken.length > 1, String(spoken));

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '边界用例：全部通过');
  process.exit(fails ? 1 : 0);
})();
