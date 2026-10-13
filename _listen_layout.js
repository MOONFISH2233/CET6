/* 听力页新布局 + 时间点的实测（390×780）：
   1) 一进来只看到题目，原文不显示
   2) 「看原文与翻译」能展开并跳到最后
   3) 「听这题」的时间点在录音里是不是句子开头（拿真实音频的波形验证） */
const { chromium } = require('D:/npm/node_modules/playwright');
// 默认打本地；带 --live 就打线上（部署后复测用）
const LIVE = process.argv.includes('--live');
const BASE = LIVE ? 'http://47.109.130.65:5173/cet6' : 'http://127.0.0.1:8765';
const SET = '2024-06-1';
console.log('目标: ' + BASE);
let fails = 0;
const ck = (n, c, e) => { console.log((c ? '  OK   ' : '  FAIL ') + n + (c ? '' : '   <<< ' + (e || ''))); if (!c) fails++; };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 140)); });

  await p.goto(BASE + '/p/' + SET + '/listening.html?v=' + Date.now(), { waitUntil: 'networkidle' });
  await p.waitForTimeout(1200);

  console.log('== 一进来看到什么 ==');
  const first = await p.evaluate(() => {
    const box = document.getElementById('audText');
    const q = document.querySelector('.q');
    return {
      textOpen: box.open,
      textVisible: !!(box.offsetParent),
      textBodyVisible: (() => { const bd = box.querySelector('.aud-text-body');
                                return bd ? !!(bd.offsetParent) : null; })(),
      firstQTop: Math.round(q.getBoundingClientRect().top),
      firstQText: q.querySelector('.q-no').textContent.trim(),
      cardTop: Math.round(document.getElementById('audCard').getBoundingClientRect().top),
      btn: !!document.getElementById('audShowText'),
      docH: document.documentElement.scrollHeight,
    };
  });
  console.log('  ' + JSON.stringify(first));
  ck('原文默认收起', first.textOpen === false, String(first.textOpen));
  ck('原文内容不可见', first.textBodyVisible === false, String(first.textBodyVisible));
  ck('播放器在顶部、题目紧随其后', first.cardTop < first.firstQTop, JSON.stringify(first));
  ck('题目在首屏内（不用滚很远）', first.firstQTop < 900, String(first.firstQTop));
  ck('有「看原文与翻译」按钮', first.btn);
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/layout-01-top.png' });

  console.log('== 点「看原文与翻译」==');
  await p.click('#audShowText');
  await p.waitForTimeout(1400);
  const after = await p.evaluate(() => {
    const box = document.getElementById('audText');
    // ⚠️ 要量折叠条（summary），不是整个 details —— 展开后它有两万像素高
    const head = box.querySelector('summary');
    const r = head.getBoundingClientRect();
    return { open: box.open, bodyVisible: !!(box.querySelector('.aud-text-body').offsetParent),
             headTop: Math.round(r.top),
             atBottom: r.top >= -40 && r.top < window.innerHeight,
             lines: box.querySelectorAll('.tr-line').length };
  });
  console.log('  ' + JSON.stringify(after));
  ck('展开成功', after.open === true);
  ck('内容显示了', after.bodyVisible === true);
  ck('滚到了原文（在视口里）', after.atBottom, JSON.stringify(after));
  ck('原文含逐句内容', after.lines > 30, String(after.lines));
  await p.screenshot({ path: 'D:/学习/六级/build/_shots/layout-02-text.png' });

  console.log('== 两个开关（显示答案 / 中文对照）在不在最上面 ==');
  await p.evaluate(() => window.scrollTo(0, 0));   // ⚠️ 上一段点过「看原文」，页面已经滚到底了
  await p.waitForTimeout(400);
  const tools = await p.evaluate(() => {
    // ⚠️ 页头也用 .tools 类（4 处），工具栏要限定在 .wrap 里才拿得准
    const t = document.querySelector('.wrap .tools');
    const firstQ = document.querySelector('.q');
    const mk = document.getElementById('meRoot');
    return {
      hasTools: !!t,
      top: t ? Math.round(t.getBoundingClientRect().top) : -1,
      qTop: Math.round(firstQ.getBoundingClientRect().top),
      ansBtn: (document.getElementById('ansBtn') || {}).textContent || '',
      zhBtn: (document.getElementById('zhBtn') || {}).textContent || '',
      btnCount: (document.querySelector('.wrap .tools') || { querySelectorAll: () => [] })
        .querySelectorAll('button').length,
      bodyCls: document.body.className,
      // 题目里的中文
      qZhHidden: (() => {
        const zh = firstQ.querySelector('.zh');
        return zh ? getComputedStyle(zh).display === 'none' : null;
      })(),
      qEnVisible: (() => {
        const en = firstQ.querySelector('.en');
        return en ? getComputedStyle(en).display !== 'none' : null;
      })(),
    };
  });
  console.log('  ' + JSON.stringify(tools));
  ck('工具栏在（且在视口内）', tools.hasTools && tools.top > 0 && tools.top < 780, JSON.stringify(tools));
  ck('工具栏在题目之上', tools.top < tools.qTop, tools.top + ' vs ' + tools.qTop);
  // 工具栏一共三个：显示答案 / 中文对照 / 深色
  ck('工具栏三个按钮都在', tools.btnCount === 3, String(tools.btnCount));
  ck('「显示答案」按钮在', /答案/.test(tools.ansBtn), tools.ansBtn);
  ck('「中文对照」按钮在', /中文/.test(tools.zhBtn), tools.zhBtn);
  ck('听力页默认隐藏中文', tools.qZhHidden === true, String(tools.qZhHidden));
  ck('题干英文仍在', tools.qEnVisible === true, String(tools.qEnVisible));

  console.log('== 点「中文对照」能看回中文 ==');
  await p.locator('#zhBtn').click();
  await p.waitForTimeout(500);
  const shown = await p.evaluate(() => {
    const zh = document.querySelector('.q .zh');
    return { disp: zh ? getComputedStyle(zh).display : null,
             cls: document.body.className,
             label: (document.getElementById('zhBtn') || {}).textContent };
  });
  console.log('  ' + JSON.stringify(shown));
  ck('点后题干中文显示出来', shown.disp !== 'none', JSON.stringify(shown));
  // 点完中文亮起来 → 按钮文字变成「中文对照」（它的语义是「点我就切中文对照」）
  ck('按钮文字已切换', /中文对照/.test(shown.label), shown.label);

  console.log('== 关键：中文开关只该管题干，选项的中文要一直在 ==');
  const scope = await p.evaluate(async () => {
    const q = document.querySelector('.q');
    const stemZh = q.querySelector('.q-stem .zh');
    const optZh = q.querySelector('.opts .zh');
    const read = () => ({
      stemZh: stemZh ? getComputedStyle(stemZh).display : null,
      optZh: optZh ? getComputedStyle(optZh).display : null,
    });
    const on = read();                       // 此刻中文是开着的
    document.getElementById('zhBtn').click();   // 关掉
    await new Promise(r => setTimeout(r, 250));
    const off = read();
    document.getElementById('zhBtn').click();   // 再打开
    await new Promise(r => setTimeout(r, 250));
    const back = read();
    return { on, off, back };
  });
  console.log('  中文开着: ' + JSON.stringify(scope.on));
  console.log('  中文关掉: ' + JSON.stringify(scope.off));
  console.log('  再打开: ' + JSON.stringify(scope.back));
  ck('开着时题干与选项的中文都在', scope.on.stemZh !== 'none' && scope.on.optZh !== 'none',
     JSON.stringify(scope.on));
  ck('关掉时题干中文藏起来', scope.off.stemZh === 'none', JSON.stringify(scope.off));
  ck('关掉时选项中文也藏起来', scope.off.optZh === 'none', JSON.stringify(scope.off));
  ck('再打开中文回来', scope.back.stemZh !== 'none' && scope.back.optZh !== 'none',
     JSON.stringify(scope.back));
  await p.waitForTimeout(200);

  console.log('== 题目行的「听这题」还在不在 ==');
  await p.evaluate(() => window.scrollTo(0, 0));
  await p.waitForTimeout(300);
  ck('25 个按钮都在', await p.locator('.aud-q').count() === 25);

  console.log('== 时间点：跳到那一刻，看前后 0.4 秒的能量（验证是不是句子开头）==');
  // 用 AudioContext 解码一小段，看点击后的瞬间是不是「由静到动」
  const probe = await p.evaluate(async () => {
    const a = document.getElementById('audPlayer');
    const t = parseFloat(document.querySelectorAll('.aud-q')[0].dataset.aud);
    a.currentTime = Math.max(0, t - 6);        // 往前多取一点，便于观察
    await new Promise(r => { a.addEventListener('seeked', r, { once: true }); setTimeout(r, 3000); });
    return { jumpTo: t, now: a.currentTime };
  });
  console.log('  第 1 题按钮 → ' + probe.jumpTo + 's（实际停在 ' + probe.now.toFixed(1) + 's）');
  ck('跳转生效', Math.abs(probe.now - Math.max(0, probe.jumpTo - 6)) < 3, JSON.stringify(probe));
  ck('时间点在合理范围内（不在篇外）', probe.jumpTo > 35 && probe.jumpTo < 210, String(probe.jumpTo));

  console.log('\n报错: ' + (errs.join(' | ') || '（无）'));
  ck('无 JS 报错', errs.length === 0, errs.join(' | '));
  await b.close();
  console.log(fails ? '!!! ' + fails + ' 项未通过' : '听力页布局：全部通过');
  process.exit(fails ? 1 : 0);
})();
