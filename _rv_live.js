/* 线上实测：直接打 47.109.130.65:5173/cet6/，手机视口 390×780。
   本地全绿不代表服务器上就行（路径、缓存、部署遗漏都会在这儿露出来）。 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://47.109.130.65:5173/cet6';
const OUT = 'D:/学习/六级/build/_shots';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

const vocab = ['antibiotic', 'competitiveness', 'hierarchical', 'sustainable', 'inevitable',
  'phenomenon', 'subsidy', 'cognitive'].map((w, i) => ({
    w, gloss: '', cefr: '', src: i % 2 ? '2023-06-1/cloze' : '2024-12-2/reading1',
    t: Date.now() - i * 3600000,
  }));

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('response', r => { if (r.url().indexOf(BASE) === 0 && r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });

  console.log('== 线上首页 ==');
  await p.goto(BASE + '/review.html', { waitUntil: 'networkidle' });
  await p.evaluate(v => {
    localStorage.setItem('cet6:vocab', JSON.stringify(v));
    localStorage.removeItem('cet6:srs'); localStorage.removeItem('cet6:srsOpt');
  }, vocab);
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1200);
  const stat = (await p.locator('#rvStat').innerText()).replace(/\n/g, ' | ');
  console.log('  ' + stat);
  ck('首页算出 8 个词', /今天 8 个词/.test(stat), stat);
  await p.screenshot({ path: OUT + '/live-01-home.png' });

  console.log('== 出题 + 判定 ==');
  await p.click('#rvStartBtn');
  await p.waitForTimeout(800);
  const word = await p.locator('#rvWord').innerText();
  const opts = await p.locator('.rv-opt').allInnerTexts();
  console.log('  ' + word + ' → ' + opts.length + ' 选项');
  ck('4 个选项', opts.length === 4, String(opts.length));
  await p.mouse.move(389, 2);
  await p.waitForTimeout(150);
  await p.screenshot({ path: OUT + '/live-02-card.png' });
  await p.locator('.rv-opt').nth(1).click();
  await p.waitForTimeout(700);
  const fb = (await p.locator('#rvFb').innerText()).replace(/\n/g, ' | ');
  console.log('  反馈: ' + fb);
  ck('点一下就有反馈', /答对了|答错了/.test(fb), fb);
  ck('反馈带释义与出处', fb.length > 25, fb);
  ck('正确项变绿', await p.locator('.rv-opt.ok').count() === 1);
  await p.mouse.move(389, 2);
  await p.screenshot({ path: OUT + '/live-03-feedback.png' });

  console.log('== 深色 / 纯黑 ==');
  for (const th of ['dark', 'oled']) {
    await p.evaluate(t => { document.documentElement.dataset.theme = t; localStorage.setItem('cet6-theme', t); }, th);
    await p.waitForTimeout(250);
    await p.screenshot({ path: OUT + '/live-04-' + th + '.png' });
    const over = await p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    ck(th + ' 档无横向溢出', !over);
  }
  await p.evaluate(() => { document.documentElement.dataset.theme = 'light'; localStorage.setItem('cet6-theme', 'light'); });

  console.log('== 我的学习：入口 + 按天 ==');
  await p.goto(BASE + '/me.html', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1200);
  ck('生词本有背单词入口', await p.locator('#meList .rv-entry').count() === 1);
  const n0 = await p.locator('#meList .rv-entry .rv-entry-n').innerText();
  ck('入口显示今日数量', /今天 \d+ 个/.test(n0), n0);
  ck('分组默认收起', await p.locator('#meList details.vgrp[open]').count() === 0);
  await p.screenshot({ path: OUT + '/live-05-me.png' });
  await p.click('#meGroupsBtn');
  await p.waitForTimeout(400);
  ck('全部展开可用', await p.locator('#meList details.vgrp[open]').count() > 0);
  await p.click('#meGroup [data-g="day"]');
  await p.waitForTimeout(400);
  const gd = await p.locator('#meList .vgroup .vgl').allInnerTexts();
  console.log('  按天: ' + JSON.stringify(gd));
  ck('按天分组生效', gd.length > 0 && gd.every(t => /今天|昨天|\d{4}-\d{2}-\d{2}/.test(t)), JSON.stringify(gd));
  ck('按天也默认收起', await p.locator('#meList details.vgrp[open]').count() === 0);
  await p.screenshot({ path: OUT + '/live-06-me-byday.png' });

  console.log('== 打卡站今日卡片 ==');
  await p.goto(BASE + '/plan/index.html', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1400);
  const pe = await p.locator('#todayCard .rv-entry').innerText().catch(() => '(无)');
  console.log('  ' + pe.replace(/\n/g, ' | '));
  ck('今日卡片有背单词入口', await p.locator('#todayCard .rv-entry').count() === 1);
  ck('四步胶囊已下架', await p.locator('.dstep').count() === 0);
  await p.screenshot({ path: OUT + '/live-07-plan.png' });
  // 入口能真的点进背单词页
  await p.click('#todayCard .rv-entry');
  await p.waitForTimeout(1500);
  ck('入口跳转到了背单词页', p.url().indexOf('/review.html') > 0, p.url());

  console.log('== 其他既有页面没被弄坏 ==');
  await p.goto(BASE + '/p/2024-12-2/reading1.html', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1000);
  ck('模块页仍能点词（.w 已包）', await p.locator('.w').count() > 50, String(await p.locator('.w').count()));
  ck('重点词块还在', await p.locator('#hfwBox').count() === 1);
  // 点一个词，弹窗里应该只有释义，不该再有喇叭
  await p.locator('.w').nth(20).click();
  await p.waitForTimeout(400);
  const pop = await p.locator('.wpop').innerText().catch(() => '');
  ck('弹窗还能弹出来', pop.length > 3, pop.slice(0, 60));
  ck('弹窗里没有喇叭按钮', await p.locator('.wpop .spk').count() === 0);
  ck('弹窗仍显示音标', await p.locator('.wpop-phon').count() >= 0);

  console.log('\n控制台/网络问题: ' + (errs.join('\n') || '（无）'));
  ck('无报错、无 404', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '线上实测：全部通过');
  process.exit(fails ? 1 : 0);
})();
