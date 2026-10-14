/* 背单词页的三种范围（默认 / 某天 / 某套 / 重点标记）实测 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

const vocab = ['antibiotic', 'competitiveness', 'hierarchical', 'sustainable', 'inevitable', 'phenomenon']
  .map((w, i) => ({ w, gloss: '', cefr: '', src: i % 2 ? '2023-06-1/cloze' : '2024-06-2/reading1',
                    t: Date.now() - Math.floor(i / 3) * 86400000 }));
const today = new Date();
const todayKey = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) +
                 '-' + ('0' + today.getDate()).slice(-2);

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));

  await p.goto(BASE + '/review.html');
  await p.evaluate(v => {
    localStorage.setItem('cet6:vocab', JSON.stringify(v));
    localStorage.setItem('cet6:srs', JSON.stringify({}));
  }, vocab);

  console.log('== 默认（今天该背的）==');
  await p.goto(BASE + '/review.html?x=' + Date.now());
  await p.waitForTimeout(1300);
  let t = (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | ');
  console.log('  ' + t);
  ck('默认只算今天的量', /今天 6 个词/.test(t), t);
  ck('有重点标记入口', await p.locator('.rv-starlink').count() === 1);

  console.log('== ?day=（这一天的词）==');
  await p.goto(BASE + '/review.html?day=' + todayKey + '&x=' + Date.now());
  await p.waitForTimeout(1300);
  t = (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | ');
  console.log('  ' + t);
  ck('筛出今天收的 3 个词', /「' + todayKey + '」3 个词/.test(t) || /3 个词/.test(t), t);
  ck('提示里带日期', t.indexOf(todayKey) >= 0, t);
  ck('给了「回到今天该背的」', /回到今天该背的/.test(t));

  console.log('== ?set=（某一套的词）==');
  await p.goto(BASE + '/review.html?set=2023-06-1&x=' + Date.now());
  await p.waitForTimeout(1300);
  t = (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | ');
  console.log('  ' + t);
  ck('筛出这套的 3 个词', /3 个词/.test(t), t);
  ck('显示的是中文套名', /2023年6月 · 第1套/.test(t), t);
  ck('开始按钮可用', !(await p.locator('#rvStartBtn').isDisabled()));

  console.log('== 点开始背，确认出的是这套的词 ==');
  await p.click('#rvStartBtn');
  await p.waitForTimeout(1000);
  const st = await p.evaluate(() => ({
    word: document.getElementById('rvWord').textContent,
    count: document.getElementById('rvCount').textContent,
  }));
  console.log('  ' + JSON.stringify(st));
  ck('进度是 1 / 3（只背这套的 3 个）', /1 \/ 3/.test(st.count), st.count);
  ck('出的是这套的词', ['competitiveness', 'sustainable', 'phenomenon'].indexOf(st.word.toLowerCase()) >= 0,
     st.word);

  console.log('== 标记一个词，再看标记列表 ==');
  // 「重点标记」按钮在答题反馈里 —— 先答一题才会出现
  await p.locator('.rv-opt').first().click();
  await p.waitForTimeout(500);
  await p.click('#rvFb [data-act="star"]');
  await p.waitForTimeout(400);
  const starred = await p.evaluate(() => {
    const S = JSON.parse(localStorage.getItem('cet6:srs') || '{}');
    return Object.keys(S).filter(k => S[k] && S[k].star);
  });
  console.log('  标了: ' + JSON.stringify(starred));
  ck('标记写进了 cet6:srs', starred.length === 1, JSON.stringify(starred));
  await p.goto(BASE + '/review.html?star=1&x=' + Date.now());
  await p.waitForTimeout(1300);
  t = (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | ');
  console.log('  ' + t);
  ck('标记列表里有这 1 个词', /1 个词/.test(t) && /重点标记/.test(t), t);
  ck('标记页也能开始背', !(await p.locator('#rvStartBtn').isDisabled()));
  await p.click('#rvStartBtn');
  await p.waitForTimeout(900);
  ck('背的就是那个标记词', (await p.locator('#rvWord').innerText()).toLowerCase() === starred[0], starred[0]);

  console.log('== 生词本里的「背这组」按钮 ==');
  await p.goto(BASE + '/me.html?x=' + Date.now());
  await p.waitForTimeout(1300);
  const n = await p.locator('#meList .vgo').count();
  console.log('  按套卷视图: ' + n + ' 个「背这组」');
  ck('每个分组都有按钮', n >= 2, String(n));
  const href = await p.locator('#meList .vgo').first().getAttribute('href');
  console.log('  第一个 href: ' + href);
  ck('指向 review.html?set=', /^review\.html\?set=/.test(href), href);
  await p.click('#meGroup [data-g="day"]');
  await p.waitForTimeout(400);
  const href2 = await p.locator('#meList .vgo').first().getAttribute('href');
  console.log('  按天视图第一个 href: ' + href2);
  ck('按天时指向 ?day=', /^review\.html\?day=/.test(href2), href2);
  await p.click('#meList .vgo').catch(() => {});
  await p.waitForTimeout(1300);
  ck('点进去就是那个范围', /个词/.test(await p.locator('#rvStat').innerText()),
     await p.locator('#rvStat').innerText());

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '范围背词：全部通过');
  process.exit(fails ? 1 : 0);
})();
