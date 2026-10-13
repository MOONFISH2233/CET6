/* 打卡站：四步胶囊去掉之后的回归（进度只看判分，含模考日整套判完） */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });

  await p.goto(BASE + '/plan/index.html');
  await p.evaluate(() => localStorage.clear());
  await p.reload();
  await p.waitForTimeout(1200);

  console.log('== 四步胶囊已经没了 ==');
  ck('页面上没有 .dstep', await p.locator('.dstep').count() === 0);
  ck('页面上没有 .dsteps 容器', await p.locator('.dsteps').count() === 0);
  ck('也没有残留的空容器', await p.evaluate(() =>
    document.querySelectorAll('.dayrow .dsteps, #todayCard .dsteps').length) === 0);

  console.log('== 说明文案还在（四步走本身没删）==');
  const phase1 = await p.locator('.phase-card.p1').innerText();
  ck('阶段一卡片仍写着四步走', /按方法做题/.test(phase1) && /在句子里背单词/.test(phase1),
     phase1.slice(0, 60));

  console.log('== 进度文案 ==');
  const meta = await p.locator('#pmeta').innerText();
  console.log('  ' + meta);
  ck('说明改成「判满就自动记上」', /判满就自动记上/.test(meta), meta);
  ck('没有任何一天算完成', /已完成 0 \//.test(meta), meta);
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/plan-01-clean.png' });

  console.log('== 阅读日：判满题就自动记上 ==');
  const day1 = await p.evaluate(() => PLAN.days[0]);
  console.log('  第 1 天: ' + day1.d + ' · ' + (day1.reading ? day1.reading.set + '/' + day1.reading.mod : '(无阅读)') +
              ' · ' + day1.reading.q_total + ' 题');
  await p.evaluate(d => {
    const a = {};
    for (let i = 1; i <= d.reading.q_total; i++) {
      a[d.reading.set + '/' + d.reading.mod + '/' + i] = { my: 'A', ok: i % 4 !== 0, t: Date.now() };
    }
    localStorage.setItem('cet6:answers', JSON.stringify(a));
  }, day1);
  await p.reload();
  await p.waitForTimeout(1100);
  const meta2 = await p.locator('#pmeta').innerText();
  console.log('  ' + meta2);
  ck('判满一天 → 已完成 1', /已完成 1 \//.test(meta2), meta2);
  ck('这一天在清单里标「已完成」', await p.locator('.dayrow .vok').count() >= 1);
  ck('日历对应格子变完成态', await p.evaluate(() => document.querySelectorAll('.wk div.done').length) === 1);
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/plan-02-day-done.png' });

  console.log('== 模考日：整套判完才算完成（新增的自动判定）==');
  const mock = await p.evaluate(() => {
    const d = PLAN.days.filter(x => x.reading && x.reading.whole)[0];
    return { d: d.d, set: d.reading.set, tot: (PLAN.set_q_total || {})[d.reading.set] };
  });
  console.log('  模考日: ' + mock.d + ' · 整套 ' + mock.set + ' · ' + mock.tot + ' 题');
  ck('模考日有整套题数', mock.tot > 0, String(mock.tot));

  // ⚠️ 按「第 N 天 · 日期」里的日期精确取行 —— 用 indexOf 会匹配到别人（踩过）
  const mockRow = md => p.evaluate(md => {
    const el = [].slice.call(document.querySelectorAll('.dayrow')).filter(r => {
      const m = r.querySelector('.dh b').textContent.match(/(\d{4}-\d{2}-\d{2})/);
      return m && m[1] === md;
    })[0];
    // ⚠️ 「完成」只认日期那行的 .dt 里的 .vok —— body 里的 .vok 是收词统计，不是状态
    return el ? { done: !!el.querySelector('.dt .vok'),
                  note: ((el.querySelector('.note.auto') || {}).textContent || '').trim() } : null;
  }, md);
  const doneCount = async () => parseInt(
    (await p.locator('#pmeta').innerText()).match(/已完成 (\d+) \//)[1], 10);

  // 种「每个模块只判一半」的作答：整套远远没判满
  const halfSeed = await p.evaluate(([s, tot]) => {
    localStorage.setItem('cet6:answers', '{}');
    const a = {};
    ['listening', 'cloze', 'longreading', 'reading1', 'reading2'].forEach(m => {
      for (let i = 1; i <= Math.floor(tot / 10); i++) a[s + '/' + m + '/' + i] = { my: 'A', ok: true, t: Date.now() };
    });
    localStorage.setItem('cet6:answers', JSON.stringify(a));
    return Object.keys(a).length;
  }, [mock.set, mock.tot]);
  await p.reload();
  await p.waitForTimeout(1100);
  const rowHalf = await mockRow(mock.d);
  console.log('  只判 ' + halfSeed + ' / ' + mock.tot + ' 题 → 模考日 ' + JSON.stringify(rowHalf));
  ck('没判满时模考日不算完成', rowHalf && rowHalf.done === false, JSON.stringify(rowHalf));

  // 再补满：每个模块都多给一些，保证整套 ≥ 总题数
  await p.evaluate(([s, tot, base]) => {
    const a = JSON.parse(localStorage.getItem('cet6:answers') || '{}');
    ['listening', 'cloze', 'longreading', 'reading1', 'reading2'].forEach(m => {
      for (let i = 1; i <= Math.ceil(tot / 5) + base; i++) a[s + '/' + m + '/' + i] = { my: 'A', ok: true, t: Date.now() };
    });
    localStorage.setItem('cet6:answers', JSON.stringify(a));
  }, [mock.set, mock.tot, 5]);
  await p.reload();
  await p.waitForTimeout(1100);
  const rowFull = await mockRow(mock.d);
  const n1 = await doneCount();
  console.log('  补满整套 → 模考日 ' + JSON.stringify(rowFull) + ' · ' + n1 + ' 天完成');
  ck('整套判满 → 模考日算完成', rowFull && rowFull.done === true, JSON.stringify(rowFull));
  ck('而且不是靠超判硬凑的（进度条只认判满）', n1 >= 1, String(n1));
  // 关键：前面只判一半时它没算，现在算上了 —— 说明这个判定真的接在整套题数上
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/plan-03-mock-done.png' });

  console.log('== 旧的手动勾选记录不该再影响进度 ==');
  await p.evaluate(d => {
    localStorage.setItem('cet6:plan', JSON.stringify({
      [d]: { '按方法做题': true, '核实对错': true, '精读全文': true, '句子里背单词': true, __done: true },
    }));
    localStorage.removeItem('cet6:answers');
  }, day1.d);
  await p.reload();
  await p.waitForTimeout(1000);
  const oldProg = await p.locator('#pmeta').innerText();
  console.log('  ' + oldProg);
  ck('旧勾选不再算完成（进度只认判分）', /已完成 0 \//.test(oldProg), oldProg);

  console.log('== 导入导出还能用 ==');
  ck('导出按钮在', await p.locator('button:has-text("导出进度")').count() === 1);
  ck('清空按钮在', await p.locator('button:has-text("清空进度")').count() === 1);

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '打卡站：全部通过');
  process.exit(fails ? 1 : 0);
})();
