/* 设计一致性检查：把新页面的关键元素和既有页面的同类元素逐项比 computed style。
   不只是「看着像」—— 变量、圆角、按钮底色、字体、三档主题都拿数值比。 */
const { chromium } = require('D:/npm/node_modules/playwright');
const BASE = 'http://127.0.0.1:8765';
const vocab = ['antibiotic', 'competitiveness', 'hierarchical', 'sustainable', 'inevitable']
  .map((w, i) => ({ w, gloss: '', cefr: '', src: '2023-06-1/cloze', t: Date.now() - i * 1000 }));

let fails = 0;
function ck(n, cond, extra) {
  console.log((cond ? '  OK   ' : '  FAIL ') + n + (cond ? '' : '   <<< ' + (extra || '')));
  if (!cond) fails++;
}

const probe = (sel, props) => `(() => {
  const e = document.querySelector(${JSON.stringify(sel)});
  if (!e) return null;
  const c = getComputedStyle(e);
  const o = {};
  ${JSON.stringify(props)}.forEach(p => { o[p] = c.getPropertyValue(p); });
  const r = e.getBoundingClientRect();
  o.__rect = Math.round(r.width) + 'x' + Math.round(r.height);
  return o;
})()`;

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 780 } });

  // ---- 参考页：既有模块页 ----
  await p.goto(BASE + '/p/2024-12-2/reading1.html');
  await p.waitForTimeout(700);
  const refCard = await p.evaluate(probe('.card', ['background-color', 'border-radius', 'box-shadow', 'border-color']));
  const refTag = await p.evaluate(probe('.card h2 .tag', ['background-color', 'color', 'border-radius', 'font-size']));
  const refOpt = await p.evaluate(probe('.opts li', ['border-radius', 'background-color', 'font-size', 'padding']));
  const refSpk = await p.evaluate(probe('.spk', ['width', 'height', 'border-radius']));
  const refBtn = await p.evaluate(probe('.qb-btn', ['background-color', 'color', 'border-radius',
    'font-size', 'font-weight', 'padding']));
  const refBody = await p.evaluate(probe('body', ['background-color', 'color', 'font-family', 'font-size']));
  const rootVars = await p.evaluate(`(() => {
    const c = getComputedStyle(document.documentElement);
    const out = {};
    ['--accent','--accent-text','--accent-soft','--accent-line','--bg-card','--fg','--radius','--radius-sm','--radius-pill','--font-en','--shadow-sm']
      .forEach(k => out[k] = c.getPropertyValue(k).trim());
    return out;
  })()`);

  // ---- 新页面：背单词 ----
  await p.goto(BASE + '/review.html');
  await p.evaluate(v => {
    localStorage.setItem('cet6:vocab', JSON.stringify(v));
    localStorage.removeItem('cet6:srs');
    localStorage.setItem('cet6-theme', 'light');
  }, vocab);
  await p.reload();
  await p.waitForTimeout(900);

  const newVars = await p.evaluate(`(() => {
    const c = getComputedStyle(document.documentElement);
    const out = {};
    ['--accent','--accent-text','--accent-soft','--accent-line','--bg-card','--fg','--radius','--radius-sm','--radius-pill','--font-en','--shadow-sm']
      .forEach(k => out[k] = c.getPropertyValue(k).trim());
    return out;
  })()`);
  console.log('== 设计变量（新页 vs 既有页） ==');
  Object.keys(rootVars).forEach(k => {
    ck(k + ' 一致', rootVars[k] === newVars[k], rootVars[k] + ' vs ' + newVars[k]);
  });

  console.log('== 元素级对比 ==');
  const nBody = await p.evaluate(probe('body', ['background-color', 'color', 'font-family', 'font-size']));
  ck('body 底色/字色/字体/字号一致',
     nBody['background-color'] === refBody['background-color'] &&
     nBody.color === refBody.color && nBody['font-family'] === refBody['font-family'] &&
     nBody['font-size'] === refBody['font-size'],
     JSON.stringify([refBody, nBody]));

  // 普通卡片：用会话里那张（首页那张是刻意加圈的主卡，跟打卡站 .today 同款，不参与比）
  await p.click('#rvStartBtn');
  await p.waitForTimeout(600);
  const nCard = await p.evaluate(probe('#rvSession .card', ['background-color', 'border-radius', 'box-shadow', 'border-color']));
  ck('卡片底/圆角/阴影/描边一致',
     ['background-color', 'border-radius', 'box-shadow', 'border-color'].every(k => nCard[k] === refCard[k]),
     JSON.stringify([refCard, nCard]));

  const nTag = await p.evaluate(probe('#rvHome h2 .tag', ['background-color', 'color', 'border-radius']));
  console.log('  标签: ' + JSON.stringify(nTag) + '   （既有: ' + JSON.stringify(refTag) + '）');
  ck('「今天」胶囊标签与既有 .tag 一致',
     !!nTag && !!refTag &&
     ['background-color', 'color', 'border-radius'].every(k => nTag[k] === refTag[k]),
     JSON.stringify([refTag, nTag]));

  const nSpk = await p.evaluate(probe('#rvSpk .spk', ['border-radius']));
  ck('喇叭按钮仍是圆形', nSpk && nSpk['border-radius'] === '50%', JSON.stringify(nSpk));

  // 鼠标挪开，别让上一处 hover/active 影响取色
  await p.mouse.move(5, 5);

  console.log('== 开始背：主按钮 ==');
  // ⚠️ 必须挪到「绝对没有元素」的角落：鼠标停在卡片上时取到的是 hover 色，
  //    之前就是因为停在按钮上，误判成「底色不是透明的」
  await p.mouse.move(389, 2);
  await p.waitForTimeout(200);
  const nOpt = await p.evaluate(probe('.rv-opt', ['background-color', 'border-radius', 'font-size', 'color']));
  console.log('  选项按钮: ' + JSON.stringify(nOpt) + '   （文章页选项: ' + JSON.stringify(refOpt) + '）');
  // 选项行的圆角用站点的小圆角档（--radius-sm，8px）—— 比文章页的 6px 略圆，是有意为之
  ck('选项圆角用的是站点变量', nOpt['border-radius'] === rootVars['--radius-sm'],
     nOpt['border-radius'] + ' vs ' + rootVars['--radius-sm']);
  ck('选项底色 = 文章页选项行（透明）', nOpt['background-color'] === refOpt['background-color'],
     nOpt['background-color']);
  ck('选项够大（拇指可点，≥40px 高）',
     nOpt.__rect.split('x')[1] >= 40, nOpt.__rect);

  await p.locator('.rv-opt').first().click();
  await p.waitForTimeout(400);
  await p.mouse.move(5, 5);

  const nNext = await p.evaluate(probe('.rv-next', ['background-color', 'color', 'border-radius', 'font-size', 'font-weight', 'padding']));
  console.log('  下一个按钮: ' + JSON.stringify(nNext) + '   （提交答案按钮: ' + JSON.stringify(refBtn) + '）');
  ck('主按钮与「提交答案」同规格',
     !!nNext && !!refBtn &&
     ['background-color', 'color', 'border-radius', 'font-size', 'font-weight', 'padding']
       .every(k => nNext[k] === refBtn[k]), JSON.stringify([refBtn, nNext]));
  const nMini = await p.evaluate(probe('#rvFb .rv-mini', ['border-radius', 'background-color', 'color']));
  ck('反馈里的小按钮是胶囊', nMini['border-radius'] === rootVars['--radius-pill'], nMini['border-radius']);
  const okColor = await p.evaluate(probe('.rv-opt.ok', ['background-color', 'color']));
  const badColor = await p.evaluate(probe('.rv-opt.bad', ['background-color', 'color']));
  console.log('  正确项: ' + JSON.stringify(okColor));
  console.log('  错误项: ' + JSON.stringify(badColor));

  console.log('== 三档主题（对比体量/溢出） ==');
  for (const th of ['light', 'dark', 'oled']) {
    await p.evaluate(t => {
      document.documentElement.dataset.theme = t;
      localStorage.setItem('cet6-theme', t);
    }, th);
    await p.waitForTimeout(220);
    const m = await p.evaluate(() => {
      const de = document.documentElement;
      const over = [];
      document.querySelectorAll('.wrap *').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.width && (r.left < -1 || r.right > window.innerWidth + 1)) {
          over.push((e.className || e.tagName) + ' ' + Math.round(r.left) + '→' + Math.round(r.right));
        }
      });
      return {
        hScroll: de.scrollWidth > de.clientWidth ? de.scrollWidth + '>' + de.clientWidth : 'no',
        bg: getComputedStyle(document.body).backgroundColor,
        card: getComputedStyle(document.querySelector('.card')).backgroundColor,
        over: over.slice(0, 4),
      };
    });
    console.log('  [' + th + '] bg=' + m.bg + ' card=' + m.card +
                ' 横向溢出=' + m.hScroll + ' 出界元素=' + JSON.stringify(m.over));
    ck(th + '：无横向溢出', m.hScroll === 'no', m.hScroll);
    ck(th + '：无元素出界', m.over.length === 0, JSON.stringify(m.over));
  }

  console.log('\n' + (fails ? '!!! ' + fails + ' 项不一致' : '设计一致性：全部通过'));
  await b.close();
  process.exit(fails ? 1 : 0);
})();
