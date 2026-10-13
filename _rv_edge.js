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

  console.log('== 发音已彻底撤掉（2026-10-13 用户要求）==');
  await p.click('#rvStartBtn');
  await p.waitForTimeout(600);
  const audio = await p.evaluate(() => ({
    spkBtn: document.querySelectorAll('.spk').length,
    dataSay: document.querySelectorAll('[data-say]').length,
    autoBox: document.querySelectorAll('#rvAuto, .rv-auto').length,
    diag: document.querySelectorAll('#rvDiag, .rv-diag').length,
    says: (window.CET6Word && window.CET6Word.speak) ? 1 : 0,
    voicesHooked: !!window.speechSynthesis && !!window.speechSynthesis.onvoiceschanged,
    phonShown: (document.getElementById('rvPhon') || {}).textContent || '',
  }));
  console.log('  ' + JSON.stringify(audio));
  ck('页面上没有喇叭按钮', audio.spkBtn === 0, String(audio.spkBtn));
  ck('没有 data-say 残留', audio.dataSay === 0, String(audio.dataSay));
  ck('没有「自动发音」勾选框', audio.autoBox === 0);
  ck('没有发音诊断面板', audio.diag === 0);
  ck('CET6Word 不再暴露 speak', audio.says === 0);
  ck('没挂 onvoiceschanged', !audio.voicesHooked);
  ck('音标照常显示', audio.phonShown.length > 2, audio.phonShown);

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '边界用例：全部通过');
  process.exit(fails ? 1 : 0);
})();
