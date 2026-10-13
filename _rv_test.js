/* 背单词页的本地实测（Playwright，390×780 手机视口）。
   跑法：node D:\学习\六级\build\_rv_test.js   （需要本地已起 8765 静态服务）
   不是构建产物，测完可删。 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
const OUT = 'D:/学习/六级/build/_shots';
const fs = require('fs');
fs.mkdirSync(OUT, { recursive: true });

const WORDS = ['antibiotic', 'competitiveness', 'hierarchical', 'sustainable', 'inevitable',
  'phenomenon', 'subsidy', 'cognitive', 'reluctant', 'infrastructure', 'ambiguous', 'deteriorate'];
const now = Date.now();
const vocab = WORDS.map((w, i) => ({
  w, gloss: '', cefr: '', src: i % 2 ? '2023-06-1/cloze' : '2024-12-2/reading1',
  t: now - i * 86400000 - 3600000,
}));

let fails = 0;
function ck(name, cond, extra) {
  console.log((cond ? '  OK   ' : '  FAIL ') + name + (cond ? '' : '   <<< ' + (extra || '')));
  if (!cond) fails++;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));

  await page.goto(BASE + '/review.html');
  await page.evaluate(v => {
    localStorage.setItem('cet6:vocab', JSON.stringify(v));
    localStorage.removeItem('cet6:srs');
    localStorage.removeItem('cet6:srsOpt');
  }, vocab);
  await page.reload();
  await page.waitForTimeout(900);

  console.log('== 首页 ==');
  const stat = await page.locator('#rvStat').innerText();
  console.log('  stat: ' + stat.replace(/\n/g, ' | '));
  ck('今日词数 = 12', /今天 12 个词/.test(stat), stat);
  ck('有 12 个新词', /新词 12 个/.test(stat), stat);
  ck('开始按钮可点', !(await page.locator('#rvStartBtn').isDisabled()));
  await page.screenshot({ path: OUT + '/01-review-home.png' });

  console.log('== 出题 ==');
  await page.click('#rvStartBtn');
  await page.waitForTimeout(600);
  const word = await page.locator('#rvWord').innerText();
  const choices = await page.locator('.rv-opt').allInnerTexts();
  console.log('  词: ' + word + '  选项: ' + choices.length);
  ck('显示英文大字', word.length > 1, word);
  ck('4 个选项', choices.length === 4, choices.length);
  ck('选项互不相同', new Set(choices).size === 4, choices.join(' / '));
  ck('进度 1 / 12', /1 \/ 12/.test(await page.locator('#rvCount').innerText()));
  ck('喇叭按钮存在', await page.locator('#rvSpk .spk').count() === 1);
  await page.screenshot({ path: OUT + '/02-review-card.png' });

  console.log('== 点一个选项 → 立刻判定 + 反馈 ==');
  const picked = await page.locator('.rv-opt').first().innerText();
  await page.locator('.rv-opt').first().click();      // 一次点击 = 选中 + 判定（判定完不再改）
  await page.waitForTimeout(400);
  const fb = await page.locator('#rvFb').innerText();
  console.log('  我点的是: ' + picked);
  console.log('  fb: ' + fb.replace(/\n/g, ' | '));
  ck('反馈出现', !(await page.locator('#rvFb').isHidden()));
  ck('反馈有对错徽标', /答对了|答错了/.test(fb), fb);
  ck('反馈有完整释义', fb.length > 20, fb);
  ck('有「太简单」按钮', await page.locator('#rvFb [data-act="easy"]').count() === 1);
  ck('有「已学会」按钮', await page.locator('#rvFb [data-act="learned"]').count() === 1);
  ck('有「再听一遍」', await page.locator('#rvFb [data-act="say"]').count() === 1);
  ck('正确项恰好一个变绿', await page.locator('.rv-opt.ok').count() === 1,
     String(await page.locator('.rv-opt.ok').count()));
  ck('选项已锁（不可再点）', await page.locator('.rv-opt').first().isDisabled());
  const srcTxt = await page.locator('#rvFb .rv-src').innerText();
  console.log('  出处: ' + srcTxt);
  ck('反馈有出处', srcTxt.length > 0, srcTxt);
  await page.screenshot({ path: OUT + '/04-review-feedback.png' });

  console.log('== 走完一轮 ==');
  for (let i = 0; i < 20; i++) {
    const next = page.locator('#rvFb [data-act="next"]');
    if (!(await next.count()) || !(await next.isVisible())) break;
    await next.click();
    await page.waitForTimeout(150);
    const opt = page.locator('.rv-opt').first();
    if (!(await opt.count()) || !(await opt.isVisible())) break;
    await opt.click();
    await page.waitForTimeout(120);
  }
  await page.waitForTimeout(700);
  const sum = await page.locator('#rvSum').innerText().catch(() => '(无)');
  console.log('  sum: ' + sum.replace(/\n/g, ' | '));
  ck('一轮结束有成绩单', /这一轮结束/.test(sum), sum);
  await page.screenshot({ path: OUT + '/05-review-summary.png' });

  console.log('== SM-2 落库 ==');
  const srs = await page.evaluate(() => JSON.parse(localStorage.getItem('cet6:srs') || '{}'));
  const keys = Object.keys(srs);
  console.log('  srs 条数: ' + keys.length);
  console.log('  样例: ' + JSON.stringify(srs[keys[0]]));
  const sample = srs[keys[0]] || {};
  ck('记录含 EF/I/n/due', ['EF', 'I', 'n', 'due'].every(k => k in sample), JSON.stringify(sample));
  ck('due 是未来时间戳', sample.due > Date.now(), String(sample.due));
  // 答错（或对新词直接判定）→ due 应为明天
  const tomorrow = new Date(); tomorrow.setHours(0, 0, 0, 0);
  const dueDay = new Date(sample.due).setHours(0, 0, 0, 0);
  ck('间隔至少 1 天', dueDay - tomorrow.getTime() >= 86400000 - 1000,
     new Date(sample.due).toISOString());
  const again = await page.locator('#rvSum .rv-sum-sub').innerText();
  console.log('  sub: ' + again);

  console.log('== 深色 / 纯黑主题 ==');
  await page.evaluate(() => localStorage.setItem('cet6-theme', 'dark'));
  await page.reload();
  await page.waitForTimeout(600);
  await page.click('#rvStartBtn').catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + '/06-review-dark.png' });
  await page.evaluate(() => { document.documentElement.dataset.theme = 'oled'; });
  await page.waitForTimeout(200);
  await page.screenshot({ path: OUT + '/07-review-oled.png' });

  console.log('== me.html：入口 + 按天分组 ==');
  await page.evaluate(() => localStorage.setItem('cet6-theme', 'light'));
  await page.goto(BASE + '/me.html');
  await page.waitForTimeout(900);
  ck('生词本顶部有背单词入口', await page.locator('#meList .rv-entry').count() === 1);
  const entryN = await page.locator('#meList .rv-entry .rv-entry-n').innerText();
  console.log('  入口文案: ' + entryN);
  ck('入口带今日数量', /今天 \d+ 个/.test(entryN), entryN);
  await page.screenshot({ path: OUT + '/08-me-entry.png' });

  const groupsSet = await page.locator('#meList .vgroup .vgl').allInnerTexts();
  console.log('  按套卷分组: ' + JSON.stringify(groupsSet));
  ck('默认按套卷分组', groupsSet.length >= 2, JSON.stringify(groupsSet));
  ck('默认高亮「按套卷」', await page.locator('#meGroup .rv-grp.on').innerText() === '按套卷');
  await page.click('#meGroup [data-g="day"]');
  await page.waitForTimeout(300);
  const groupsDay = await page.locator('#meList .vgroup .vgl').allInnerTexts();
  console.log('  按天分组: ' + JSON.stringify(groupsDay));
  ck('切到按天分组', groupsDay.length > 0 && groupsDay.every(t => /\d{4}-\d{2}-\d{2}/.test(t)),
     JSON.stringify(groupsDay));
  ck('高亮切到「按天」', await page.locator('#meGroup .rv-grp.on').innerText() === '按天');
  await page.screenshot({ path: OUT + '/09-me-byday.png' });
  await page.click('#meGroup [data-g="set"]');
  await page.waitForTimeout(250);
  ck('能切回按套卷', (await page.locator('#meList .vgroup .vgl').allInnerTexts())
     .every(t => !/\d{4}-\d{2}-\d{2}/.test(t)));

  console.log('== 打卡站今日卡片入口 ==');
  await page.goto(BASE + '/plan/index.html');
  await page.waitForTimeout(1000);
  const pentry = await page.locator('#todayCard .rv-entry').count();
  const ptxt = await page.locator('#todayCard .rv-entry').innerText().catch(() => '(无)');
  console.log('  今日卡片入口: ' + ptxt.replace(/\n/g, ' | '));
  ck('打卡站有背单词入口', pentry === 1, String(pentry));
  const href = await page.locator('#todayCard .rv-entry').getAttribute('href').catch(() => '');
  ck('指向 ../review.html', href === '../review.html', href);
  await page.screenshot({ path: OUT + '/10-plan-today.png' });

  console.log('\n== 控制台错误 ==');
  console.log(errs.length ? errs.join('\n') : '  （无）');
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));

  await browser.close();
  console.log('\n' + (fails ? '!!! ' + fails + ' 项未通过' : '全部通过'));
  process.exit(fails ? 1 : 0);
})();
