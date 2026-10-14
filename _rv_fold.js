/* 生词本分组折叠 + 发音诊断面板的实测 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

// 12 个词：3 个套卷 × 4 个日期，保证两种分法都有多组
const WORDS = ['antibiotic', 'competitiveness', 'hierarchical', 'sustainable', 'inevitable',
  'phenomenon', 'subsidy', 'cognitive', 'reluctant', 'infrastructure', 'ambiguous', 'deteriorate'];
const SETS = ['2023-06-1/cloze', '2024-06-2/reading1', '2025-12-3/listening'];
const vocab = WORDS.map((w, i) => ({
  w, gloss: '', cefr: '', src: SETS[i % 3], t: Date.now() - Math.floor(i / 3) * 86400000 - 3600000,
}));

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });

  await p.goto(BASE + '/me.html');
  await p.evaluate(v => {
    localStorage.setItem('cet6:vocab', JSON.stringify(v));
    localStorage.removeItem('cet6:vgOpen');
  }, vocab);
  await p.reload();
  await p.waitForTimeout(900);

  console.log('== 默认全部收起 ==');
  const n = await p.locator('#meList details.vgrp').count();
  const openN = await p.locator('#meList details.vgrp[open]').count();
  const itemVis = await p.locator('#meList .vitem').first().isVisible().catch(() => false);
  console.log('  分组 ' + n + ' 个，展开的 ' + openN + ' 个');
  ck('分组渲染出来了', n === 3, String(n));
  ck('默认全部收起', openN === 0, String(openN));
  ck('收起时看不到词条', itemVis === false);
  ck('有「全部展开」按钮', await p.locator('#meGroupsBtn').isVisible());
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/fold-01-collapsed.png' });

  console.log('== 点标题展开这一组 ==');
  const head = await p.locator('#meList .vgroup span').first().innerText();
  // ⚠️ 点标题**文字**，别点整条 summary：右半边有「背这组」按钮，
  //    点中心会点到它，那就变成跳转了（不是折叠）
  await p.locator('#meList details.vgrp > summary .vgl').first().click();
  await p.waitForTimeout(300);
  console.log('  展开了: ' + head);
  ck('该组展开', await p.locator('#meList details.vgrp').first().evaluate(d => d.open));
  ck('其他组仍收起', await p.locator('#meList details.vgrp[open]').count() === 1);
  ck('展开后能看到词条', await p.locator('#meList .vitem').first().isVisible());
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/fold-02-one-open.png' });

  console.log('== 再点一次收起 ==');
  // ⚠️ 点标题**文字**，别点整条 summary：右半边有「背这组」按钮，
  //    点中心会点到它，那就变成跳转了（不是折叠）
  await p.locator('#meList details.vgrp > summary .vgl').first().click();
  await p.waitForTimeout(300);
  ck('收起成功', await p.locator('#meList details.vgrp[open]').count() === 0);

  console.log('== 全部展开 / 全部收起 ==');
  await p.click('#meGroupsBtn');
  await p.waitForTimeout(300);
  ck('全部展开', await p.locator('#meList details.vgrp[open]').count() === 3);
  ck('按钮文案变「全部收起」', /收起/.test(await p.locator('#meGroupsBtn').innerText()),
     await p.locator('#meGroupsBtn').innerText());
  ck('展开后 12 条词都在', await p.locator('#meList .vitem').count() === 12,
     String(await p.locator('#meList .vitem').count()));
  await p.click('#meGroupsBtn');
  await p.waitForTimeout(300);
  ck('全部收起', await p.locator('#meList details.vgrp[open]').count() === 0);
  ck('按钮文案变回「全部展开」', /展开/.test(await p.locator('#meGroupsBtn').innerText()));

  console.log('== 展开状态要记住（刷新后） ==');
  await p.locator('#meList details.vgrp > summary .vgl').nth(1).click();
  await p.waitForTimeout(250);
  const kept = await p.locator('#meList details.vgrp').nth(1).getAttribute('data-k');
  await p.reload();
  await p.waitForTimeout(900);
  const stillOpen = await p.locator('#meList details.vgrp[open]').count();
  const openKey = await p.locator('#meList details.vgrp[open]').first().getAttribute('data-k').catch(() => null);
  console.log('  刷新前展开: ' + kept + ' → 刷新后: ' + openKey);
  ck('刷新后仍记得展开的是哪一组', stillOpen === 1 && openKey === kept, stillOpen + '/' + openKey);

  console.log('== 换分法后也折叠 ==');
  await p.click('#meGroup [data-g="day"]');
  await p.waitForTimeout(350);
  const dayN = await p.locator('#meList details.vgrp').count();
  const dayOpen = await p.locator('#meList details.vgrp[open]').count();
  console.log('  按天 → ' + dayN + ' 组，展开 ' + dayOpen);
  ck('按天也有折叠', dayN >= 3, String(dayN));
  ck('按天默认收起（key 不同，不会串）', dayOpen === 0, String(dayOpen));
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/fold-03-byday.png' });

  console.log('== 错题本 / 句子 标签下不显示分组按钮 ==');
  await p.click('.tab[data-tab="wrong"]');
  await p.waitForTimeout(300);
  ck('错题本下隐藏分组按钮', !(await p.locator('#meGroup').isVisible()));
  ck('错题本下隐藏全局折叠按钮', !(await p.locator('#meGroupsBtn').isVisible()));
  await p.click('.tab[data-tab="vocab"]');
  await p.waitForTimeout(300);

  console.log('== 发音相关的东西都不在了 ==');
  await p.goto(BASE + '/review.html');
  await p.waitForTimeout(900);
  ck('诊断面板已移除', await p.locator('#rvDiag').count() === 0);
  ck('自动发音设置项已移除', await p.locator('#rvAuto').count() === 0);
  ck('页面上没有喇叭按钮', await p.locator('.spk').count() === 0);
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/fold-04-nosound.png' });

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '折叠 + 诊断：全部通过');
  process.exit(fails ? 1 : 0);
})();
