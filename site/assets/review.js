/* ==========================================================================
   背单词（百词斩式）：弹英文大字 → 4 选 1 中文 → 立刻反馈 + 释义 + 出处

   数据：
     词源   cet6:vocab（生词本，精读站点词收的词）—— 新词就从这个池子里取
     调度   cet6:srs   { "<词>": {EF, I, n, due, seen, ok, bad, learned, star} }
     设置   cet6:srsOpt { newPerDay: 20|30|40 }
   词义/音标来自 word.js 的词库（核心 dict.json + 兜底 dict_all.json）。

   SM-2：答对 n++，间隔 1 → 6 → round(I×EF) 天；答错 n 归零、明天必来。
         「太简单」= 直接跳到 6 天档（认识但不用细背）；「已学会」= 移出轮转。
   ⚠️ 界面只复用 style.css 的变量与既有元件（胶囊/衬线/卡片阴影/三档主题），不新造设计语言。
   ========================================================================== */

(function () {
  'use strict';

  var SRS_KEY = 'cet6:srs';
  var OPT_KEY = 'cet6:srsOpt';
  var VOCAB_KEY = 'cet6:vocab';
  var DAY = 86400000;
  var MAX_EF = 3.0;
  var LEARNED_DAYS = 365;

  // 页面上要用到的元素，一次抓齐（id 与 gen_site.build_review 一致）
  var el = {};
  ['rvHome', 'rvStat', 'rvStartBtn', 'rvHomeNote', 'rvSession', 'rvCount', 'rvBar',
   'rvCard', 'rvWord', 'rvPhon', 'rvChoices', 'rvFb', 'rvSum', 'rvOpt'].forEach(function (id) {
    el[id] = document.getElementById(id);
  });

  var mode = 'home';
  var session = null;
  var opt = load(OPT_KEY, null) || { newPerDay: 20 };
  if ([20, 30, 40].indexOf(+opt.newPerDay) < 0) opt.newPerDay = 20;

  // ------------------------------------------------------------ 只背一部分
  // 「这一天的词」「这一套的词」「重点标记的词」—— 生词本的分组按钮和标记入口都用它。
  // 地址带参数（?day= / ?set= / ?star=1）就是为了能从别的页面点进来。
  var FILTER_MODE = 0;      // 0 = 今天该背的（默认）
  var FILTER_KEY = '';      // 拿来匹配的原始值（日期 '2026-10-13' 或套次 '2023-06-1'）
  var FILTER_LABEL = '';    // 显示用的名字（套次会翻成「2023年6月 · 第1套」）
  var FILTER_IDS = null;    // 按套次筛时的词集合（键 = 小写单词）

  function readFilter() {
    var q = {};
    (location.search || '').replace(/^\?/, '').split('&').forEach(function (kv) {
      if (!kv) return;
      var i = kv.indexOf('=');
      var k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i));
      var v = i < 0 ? '' : decodeURIComponent(kv.slice(i + 1));
      q[k] = v;
    });
    FILTER_IDS = null;
    FILTER_KEY = FILTER_LABEL = '';
    if (q.day) { FILTER_MODE = 1; FILTER_KEY = FILTER_LABEL = q.day; return; }
    if (q.set) {
      FILTER_MODE = 2;
      FILTER_KEY = q.set;                                  // ⚠️ 匹配要用原始 key
      FILTER_LABEL = (((window.CET6_LABELS || {}).sets || {})[q.set]) || q.set;
      return;
    }
    if (q.star) { FILTER_MODE = 3; FILTER_LABEL = '重点标记的词'; return; }
    FILTER_MODE = 0;
  }

  // 按套次筛：先把这套的词集合建出来（用 src 前缀直接判，别经 passFilter ——
  // 建集合的过程中集合本身还是空的，绕回去会自己把自己判成「不在范围内」）
  function buildSetIds(vocab) {
    if (FILTER_MODE !== 2 || FILTER_IDS) return;
    var ids = {};
    vocab.forEach(function (v) {
      if (String(v.src || '').split('/')[0] === FILTER_KEY) ids[String(v.w || '').toLowerCase()] = 1;
    });
    FILTER_IDS = ids;
  }

  function passFilter(v, S) {
    var w = String(v.w || '').toLowerCase();
    if (FILTER_MODE === 0) return true;
    if (FILTER_MODE === 1) {                    // 某一天收的词
      var t = v.t || 0;
      if (!t) return false;
      var d = new Date(t);
      var key = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) +
                '-' + ('0' + d.getDate()).slice(-2);
      return key === FILTER_KEY;
    }
    if (FILTER_MODE === 2) {                    // 某一套卷收的词
      // ⚠️ 判空要用「有没有键」：空对象是 truthy，写 if (FILTER_IDS) 会永远走进去、
      //    结果全是 false（踩过：?set= 筛不出任何词）
      if (FILTER_IDS && Object.keys(FILTER_IDS).length) return !!FILTER_IDS[w];
      return String(v.src || '').split('/')[0] === FILTER_KEY;
    }
    if (FILTER_MODE === 3) return !!(S[w] && S[w].star);
    return true;
  }

  function starCount() {
    var S = srs(), n = 0;
    for (var k in S) if (S.hasOwnProperty(k) && S[k] && S[k].star) n++;
    return n;
  }

  // 「背这组」的地址（me.html 的分组按钮用它）—— 换个范围就重载页面，逻辑最省事
  function scopeHref(param, value) {
    return 'review.html?' + param + '=' + encodeURIComponent(value);
  }

  // ------------------------------------------------------------ 存取

  function load(key, def) {
    try { var s = localStorage.getItem(key); return s ? JSON.parse(s) : def; }
    catch (e) { return def; }
  }
  function save(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function srs() {
    var m = load(SRS_KEY, {});
    return (m && typeof m === 'object' && !Array.isArray(m)) ? m : {};
  }

  // 生词本里删掉的词，调度记录也别留着烂在 localStorage 里（「已学会」的留着，它还有用）
  function prune(S) {
    var vocab = load(VOCAB_KEY, []), keep = {}, dropped = 0;
    if (Array.isArray(vocab)) vocab.forEach(function (v) {
      keep[String(v.w || '').toLowerCase()] = 1;
    });
    if (!Object.keys(keep).length) return S;      // 生词本空了：宁可先不动，等下次有词再清
    for (var k in S) {
      if (S.hasOwnProperty(k) && !keep[k] && !S[k].learned) { delete S[k]; dropped++; }
    }
    if (dropped) save(SRS_KEY, S);
    return S;
  }

  function dayStart(t) {
    var d = new Date(t || Date.now());
    return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  }

  // ------------------------------------------------------------ 词义

  // word.js 的词库：先核心（带 CEFR/真题频次），没有再用 ECDICT 兜底
  function glossOf(w) {
    var W = window.CET6Word;
    if (!W) return null;
    var hit = W.lookup(w);
    if (hit) return { gloss: hit.data.gloss || '', phon: phonOf(hit.data.phon), cefr: hit.data.cefr || '' };
    var ext = W.lookupAll(w);
    if (ext) return { gloss: ext.gloss || '', phon: phonOf(ext.phon), cefr: ext.tag || '', ext: true };
    return null;
  }

  // ECDICT 的音标带「英/美」前缀，核心词库不带 —— 统一成 /ˈwɜːd/ 那种裸形式
  function phonOf(p) {
    return String(p || '').replace(/^[英美]\s*/, '').trim();
  }

  function pageLink(src) {
    var labels = window.CET6_LABELS || {};
    var parts = String(src || '').split('/');
    var set = parts[0] || '', mod = parts[1] || '';
    var setTxt = (labels.sets && labels.sets[set]) || set;
    var modTxt = (labels.mods && labels.mods[mod]) || mod;
    return {
      href: (set && mod) ? 'p/' + set + '/' + mod + '.html' : '',
      text: [setTxt, modTxt].filter(Boolean).join(' · ')
    };
  }

  // ------------------------------------------------------------ 组卷

  // 今天该背哪些：到期复习 + 新词（新词 = 生词本里还没进过轮转的）
  function buildQueue(S, vocab) {
    var now = Date.now(), due = [], fresh = [];
    vocab.forEach(function (v) {
      if (!passFilter(v, S)) return;
      var w = String(v.w || '').toLowerCase();
      if (!w) return;
      var rec = S[w];
      if (!rec) { fresh.push(v); return; }
      if (rec.learned) return;
      // 指定范围（某天/某套/标记）时，「今天到没到期」不作数 —— 用户就是想现在过一遍
      if (FILTER_MODE) { due.push(v); return; }
      if (!rec.due || rec.due <= now || !rec.n) due.push(v);   // n=0：上回答错，明天必来
    });
    due.sort(function (a, b) {
      var da = (S[String(a.w).toLowerCase()] || {}).due || 0;
      var db = (S[String(b.w).toLowerCase()] || {}).due || 0;
      return da - db;
    });
    fresh.sort(function (a, b) { return (b.t || 0) - (a.t || 0); });   // 新收录的优先

    // 指定范围时不设每天新词上限（那是「今天背多少」的额度，按组背就该整组过一遍）
    var picks = FILTER_MODE ? due.concat(fresh) : due.concat(fresh.slice(0, opt.newPerDay));
    var out = [], seen = {};
    picks.forEach(function (v) {
      var w = String(v.w || '').toLowerCase();
      if (seen[w]) return;
      seen[w] = 1;
      out.push(v);
    });
    return out.slice(0, FILTER_MODE ? 200 : 48);   // 单次上限，别一口气背到吐
  }

  // 还没进轮转的下标（今天新学的那几张，本次会话内不再当新词重复收进来）
  function markNotDue(list) {
    var S = srs(), n = 0;
    list.forEach(function (v) {
      var w = String(v.w || '').toLowerCase();
      if (S[w]) return;
      S[w] = { EF: 2.5, I: 0, n: 0, due: dayStart() + DAY, seen: 0, ok: 0, bad: 0, t: Date.now() };
      n++;
    });
    if (n) save(SRS_KEY, S);
    return n;
  }

  function dueCount() {
    var S = prune(srs()), now = Date.now(), vocab = load(VOCAB_KEY, []);
    if (!Array.isArray(vocab)) vocab = [];
    buildSetIds(vocab);                         // 按套次筛的话，先把这套的词集合建出来
    var due = 0, fresh = 0, learned = 0;
    vocab.forEach(function (v) {
      var w = String(v.w || '').toLowerCase();
      if (!w) return;
      var rec = S[w];
      if (FILTER_MODE) {
        // 指定范围：只要在范围里、没标「已学会」，就该过一遍（不看今天到没到期）
        if (!passFilter(v, S)) return;
        if (rec && rec.learned) { learned++; return; }
        if (rec) due++; else fresh++;
        return;
      }
      if (!rec) { fresh++; return; }
      if (rec.learned) { learned++; return; }
      if (!rec.due || rec.due <= now || !rec.n) due++;
    });
    var freshCap = FILTER_MODE ? fresh : Math.min(fresh, opt.newPerDay);
    return {
      due: due,
      fresh: freshCap,
      rest: FILTER_MODE ? 0 : Math.max(0, fresh - opt.newPerDay),
      learned: learned,
      total: due + freshCap
    };
  }

  function start() {
    var vocab = load(VOCAB_KEY, []);
    if (!Array.isArray(vocab)) vocab = [];
    var S = srs();
    buildSetIds(vocab);
    var picks = buildQueue(prune(S), vocab);
    var cards = [], skipped = 0, missing = 0;
    picks.forEach(function (v) {
      var w = String(v.w || '').toLowerCase();
      var hit = glossOf(w);
      if (!hit || !hit.gloss) { missing++; return; }
      cards.push({
        w: w, shown: v.w, gloss: hit.gloss, phon: hit.phon, cefr: hit.cefr, ext: !!hit.ext,
        src: v.src || '',
        isNew: !S[w],
        seen: (S[w] && S[w].seen) || 0,
        ok: (S[w] && S[w].ok) || 0
      });
    });
    if (missing) console.warn('[背单词] ' + missing + ' 个词查不到释义，已跳过');

    session = {
      queue: cards, i: 0, cur: null, sel: -1, judged: false,
      ok: 0, bad: 0, known: 0, fresh: 0, again: 0
    };
    markNotDue(picks.filter(function (v) {
      return cards.some(function (c) { return c.w === String(v.w || '').toLowerCase(); });
    }));
    session.fresh = cards.filter(function (c) { return c.isNew; }).length;
    mode = 'run';
    el.rvHome.hidden = true;
    el.rvSession.hidden = false;
    if (!cards.length) { noCards(); return; }
    show();
  }

  // 4 选 1：干扰项从生词本抽，不够就拿词库里的词凑
  function makeChoices(card) {
    var pool = [];
    var vocab = load(VOCAB_KEY, []);
    if (Array.isArray(vocab)) {
      vocab.forEach(function (v) {
        if (String(v.w || '').toLowerCase() === card.w) return;
        if (v.gloss) pool.push(v.gloss);
      });
    }
    var W = window.CET6Word;
    if (W && W.all) {
      var dw = W.all();
      for (var k in dw) {
        if (k === card.w || pool.length > 220) continue;
        if (dw[k].gloss) pool.push(dw[k].gloss);
      }
    }
    var seen = {}, uniq = [];
    pool.forEach(function (g) {
      var key = String(g).slice(0, 14);
      if (!g || seen[key] || String(g) === card.gloss) return;
      seen[key] = 1;
      uniq.push(g);
    });
    // 洗牌后取 3 条（Fisher-Yates）
    for (var i = uniq.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = uniq[i]; uniq[i] = uniq[j]; uniq[j] = t;
    }
    var opts = [{ text: card.gloss, ok: true }];
    uniq.slice(0, 3).forEach(function (g) { opts.push({ text: g, ok: false }); });
    for (var m = opts.length - 1; m > 0; m--) {
      var n = Math.floor(Math.random() * (m + 1));
      var s = opts[m]; opts[m] = opts[n]; opts[n] = s;
    }
    return opts;
  }

  // ------------------------------------------------------------ 卡片

  function show() {
    var s = session;
    if (s.i >= s.queue.length) { finish(); return; }
    var card = s.queue[s.i];
    s.cur = card;
    s.sel = -1;
    s.judged = false;
    card.choices = makeChoices(card);

    el.rvCount.textContent = (s.i + 1) + ' / ' + s.queue.length;
    el.rvBar.style.width = Math.round(s.i / s.queue.length * 100) + '%';
    el.rvWord.textContent = card.shown;
    el.rvPhon.textContent = card.phon ? '/' + card.phon + '/' : '';
    el.rvFb.hidden = true;
    el.rvFb.innerHTML = '';
    el.rvChoices.hidden = false;
    el.rvChoices.innerHTML = card.choices.map(function (o, k) {
      return '<button type="button" class="rv-opt" data-i="' + k + '">' + esc(o.text) + '</button>';
    }).join('');
    el.rvCard.classList.toggle('rv-ext', !!card.ext);
    if (card.ext) el.rvCard.setAttribute('data-ext', '扩展词库');
    else el.rvCard.removeAttribute('data-ext');
  }

  function pick(i) {
    var s = session;
    if (!s || s.judged || !s.cur) return;
    s.sel = i;
    Array.prototype.forEach.call(el.rvChoices.querySelectorAll('.rv-opt'), function (b, k) {
      b.classList.toggle('on', k === i);
    });
  }

  function submit() {
    var s = session;
    if (!s || s.judged || !s.cur || s.sel < 0) return;
    s.judged = true;
    var card = s.cur;
    var ok = !!card.choices[s.sel].ok;
    var rec = applyResult(card, ok);
    if (ok) s.ok++; else { s.bad++; s.again++; }

    Array.prototype.forEach.call(el.rvChoices.querySelectorAll('.rv-opt'), function (b, k) {
      b.disabled = true;
      b.classList.toggle('ok', !!card.choices[k].ok);
      if (k === s.sel && !ok) b.classList.add('bad');
    });
    renderFb(card, ok, rec);
  }

  function renderFb(card, ok, rec) {
    var l = pageLink(card.src);
    var h = [];
    h.push('<div class="rv-fbstat ' + (ok ? 'ok' : 'bad') + '">' +
           (ok ? '✓ 答对了' : '✗ 答错了') +
           '<i>' + (card.isNew ? '新词' : '第 ' + (card.seen) + ' 次见') + '</i></div>');
    h.push('<div class="rv-def">' + esc(card.gloss) + '</div>');
    h.push('<div class="rv-fbmeta">' +
           (card.phon ? '<span>/' + esc(card.phon) + '/</span>' : '') +
           (card.cefr ? '<span class="rv-cefr">' + esc(card.cefr) + '</span>' : '') +
           (card.ext ? '<span class="rv-exttag">扩展词库</span>' : '') +
           '</div>');
    h.push('<div class="rv-src">' + (l.href
      ? '<a href="' + esc(l.href) + '">出自 ' + esc(l.text) + ' · 去原句看</a>'
      : '从重点词页收录') + '</div>');
    h.push('<div class="rv-acts">' +
      '<button type="button" class="rv-mini" data-act="star">☆ 重点标记</button>' +
      '<button type="button" class="rv-mini" data-act="learned">已学会</button>' +
      '</div>');
    h.push('<button type="button" class="rv-next" data-act="next">' +
           (session.i + 1 >= session.queue.length ? '完成' : '下一个') + ' →</button>');
    el.rvFb.innerHTML = h.join('');
    el.rvFb.hidden = false;
    el.rvChoices.hidden = true;
    el.rvFb.scrollIntoView({ block: 'nearest' });
  }

  function next() {
    var s = session;
    if (!s || !s.judged) return;
    s.i++;
    show();
  }

  // 「太简单」：认识，但不用细背 —— 直接跳到 6 天档，不占这一步的时间
  function easy() {
    var s = session;
    if (!s || !s.cur) return;
    applyResult(s.cur, true, true);
    s.known++;
    next();
  }

  // 「已学会」：移出轮转（due 推很远，数据留着，me 页能看见）
  /* 重点标记：标了就让它更常出现（下次复习提前到今天），再点一次取消 */
  function star() {
    var s = session;
    if (!s || !s.cur) return;
    var S = srs(), w = s.cur.w;
    S[w] = S[w] || { EF: 2.5, I: 0, n: 0, seen: 0, ok: 0, bad: 0, t: Date.now() };
    S[w].star = S[w].star ? 0 : 1;
    if (S[w].star) S[w].due = dayStart();
    save(SRS_KEY, S);
    var b = document.querySelector('.rv-mini[data-act="star"]');
    if (b) {
      b.classList.toggle('on', !!S[w].star);
      b.textContent = S[w].star ? '★ 已标重点' : '☆ 重点标记';
    }
  }

  function learned() {
    var s = session;
    if (!s || !s.cur) return;
    var S = srs(), w = s.cur.w;
    S[w] = S[w] || { EF: 2.5, I: 0, n: 0, seen: 0, ok: 0, bad: 0, t: Date.now() };
    S[w].seen = (S[w].seen || 0) + 1;
    S[w].learned = 1;
    S[w].due = Date.now() + LEARNED_DAYS * DAY;
    save(SRS_KEY, S);
    s.known++;
    next();
  }

  function applyResult(card, ok, easyMode) {
    var S = srs(), w = card.w;
    var r = S[w] || { EF: 2.5, I: 0, n: 0, seen: 0, ok: 0, bad: 0, t: Date.now() };
    r.seen = (r.seen || 0) + 1;
    if (ok) {
      r.ok = (r.ok || 0) + 1;
      r.n = (r.n || 0) + 1;
      if (easyMode) { r.n = Math.max(r.n, 2); r.I = 6; }
      else if (r.n <= 1) r.I = 1;
      else if (r.n === 2) r.I = 6;
      else r.I = Math.max(6, Math.round((r.I || 6) * r.EF));
      r.EF = Math.min(MAX_EF, (r.EF || 2.5) + 0.1);
    } else {
      r.bad = (r.bad || 0) + 1;
      r.n = 0;
      r.I = 1;                       // 明天必来
      r.EF = Math.max(1.3, (r.EF || 2.5) - 0.2);
    }
    r.due = dayStart() + r.I * DAY;
    r.t = Date.now();
    S[w] = r;
    save(SRS_KEY, S);
    return r;
  }

  // 注：这一版去掉了网页发音（原「🔊 再听一遍」+ 出词自动朗读 + 发音诊断面板）。
  // 用户的手机上没有英文语音包，放不出声；页面只留音标，要听音得靠词典 App。

  // ------------------------------------------------------------ 首页 / 收尾

  function renderHome() {
    // 按范围背的时候，把范围写回地址栏（刷新/分享都还在这个范围里）
    if (mode !== 'home' || FILTER_MODE) {
      try {
        var qs = FILTER_MODE === 1 ? '?day=' + encodeURIComponent(FILTER_KEY)
               : FILTER_MODE === 2 ? '?set=' + encodeURIComponent(FILTER_KEY)
               : FILTER_MODE === 3 ? '?star=1' : '';
        history.replaceState(null, '', location.pathname + qs);
      } catch (e) {}
    }

    var c = dueCount();
    mode = 'home';
    el.rvSession.hidden = true;
    el.rvHome.hidden = false;
    el.rvStartBtn.disabled = !c.total;
    el.rvStartBtn.textContent = c.total ? '开始背' : '这一组背完了';

    var h = '';
    if (!c.total) {
      h = FILTER_MODE
        ? '<b>这一组没有要背的词</b>' +
          '<span>里面的词都标过「已学会」了，或者本来就没词。</span>'
        : '<b>今天没有要背的词</b>' +
          '<span>到期复习和今天的新词都清完了。去读一篇真题，把生词收进生词本，明天就有了。</span>';
    } else if (FILTER_MODE) {
      h = '<b>「' + esc(FILTER_LABEL) + '」' + c.total + ' 个词</b>' +
          '<span>对过 / 标记过的 ' + c.due + ' 个 · 没动过的 ' + c.fresh + ' 个' +
          (c.learned ? ' · 里面的已学会 ' + c.learned + ' 个' : '') +
          ' · <a href="review.html" id="rvClearFilter">回到今天该背的</a></span>';
    } else {
      h = '<b>今天 ' + c.total + ' 个词</b>' +
          '<span>到期复习 ' + c.due + ' 个 · 新词 ' + c.fresh + ' 个' +
          (c.rest ? '（生词本里还有 ' + c.rest + ' 个排后面）' : '') +
          (c.learned ? ' · 已学会 ' + c.learned + ' 个' : '') + '</span>';
    }
    el.rvStat.innerHTML = h;

    // 重点标记：标过的词给个入口（原来标完就沉在 cet6:srs 里，没地方看 —— 用户问过）
    var sn = starCount();
    if (FILTER_MODE !== 3) {
      el.rvStat.innerHTML += '<div class="rv-starline"><a class="rv-starlink" href="review.html?star=1">★ 重点标记' +
        (sn ? ' ' + sn + ' 个' : '（还没有）') + '</a>' +
        (sn ? '<span class="rv-starhint">标过的词会提前到今天再来</span>' : '') + '</div>';
    } else if (sn) {
      el.rvStat.innerHTML += '<div class="rv-starline"><span class="rv-starhint">' +
        '点下面的「已学会」可以把它从这个列表里拿掉</span></div>';
    }

    var v = load(VOCAB_KEY, []);
    el.rvHomeNote.textContent = '生词本共 ' + (Array.isArray(v) ? v.length : 0) +
      ' 个词 · 答对的词按 1 → 6 → 更久的间隔再来，答错的明天必来。';

    el.rvOpt.querySelectorAll('.lvchip').forEach(function (b) {
      b.classList.toggle('on', +b.dataset.n === +opt.newPerDay);
    });
  }

  // 组不出题：生词本空、或词都查不到释义 —— 直接回首页，别给一张空的成绩单
  function noCards() {
    session = null;
    el.rvSession.hidden = true;
    el.rvHome.hidden = false;
    mode = 'home';
    renderHome();
    el.rvStat.innerHTML = '<b>暂时组不出题</b>' +
      '<span>生词本里的词都没查到释义，或今天没有要背的词。' +
      '去读一篇真题，点单词把生词收进生词本，再回来。</span>';
  }

  function finish() {
    var s = session || { ok: 0, bad: 0, known: 0, queue: [], fresh: 0, again: 0 };
    el.rvSession.hidden = true;
    el.rvHome.hidden = false;
    mode = 'home';

    var total = s.queue.length;
    var acc = (s.ok + s.bad) ? Math.round(s.ok / (s.ok + s.bad) * 100) : 0;
    el.rvSum.hidden = false;
    el.rvSum.innerHTML =
      '<div class="rv-sum-h">这一轮结束</div>' +
      '<div class="rv-sum-n">' + s.ok + ' 对 · ' + s.bad + ' 错' +
      (s.ok ? ' · 正确率 ' + acc + '%' : '') + '</div>' +
      '<div class="rv-sum-sub">' +
      (s.fresh ? '新词 ' + s.fresh + ' 个 · ' : '') +
      (s.known ? '标为已掌握 ' + s.known + ' 个 · ' : '') +
      '共过 ' + total + ' 张' +
      (s.again ? '（' + s.again + ' 个明天再来）' : '') + '</div>' +
      '<button type="button" class="rv-sum-go">再背一轮</button>';
    renderHome();
    el.rvSum.hidden = false;
    if (window.CET6Quotes && window.CET6Quotes.celebrate) {
      window.CET6Quotes.celebrate({ title: '背单词', ok: s.ok, bad: s.bad });
    }
  }

  // ------------------------------------------------------------ 事件

  function onCardClick(e) {
    var t = e.target.closest ? e.target.closest('button') : null;
    if (!t) return;
    if (t.classList.contains('rv-opt')) {
      // 点一下就算作答：立刻判定 + 给反馈，别让用户再找一次确认按钮
      pick(+t.dataset.i);
      submit();
      return;
    }
    var act = t.dataset.act;
    if (act === 'next') return next();
    if (act === 'easy') return easy();
    if (act === 'star') return star();
    if (act === 'learned') return learned();
    if (act === 'submit') return submit();
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest && t.closest('#rvCard')) { onCardClick(e); return; }
    if (t.classList && t.classList.contains('lvchip')) {
      var n = +t.dataset.n;
      if ([20, 30, 40].indexOf(n) >= 0) {
        opt.newPerDay = n;
        save(OPT_KEY, opt);
        if (mode === 'home') renderHome();
      }
      return;
    }
  });

  if (el.rvStartBtn) el.rvStartBtn.onclick = start;
  if (el.rvSum) el.rvSum.onclick = function (e) {
    if (e.target.closest && e.target.closest('.rv-sum-go')) start();
  };

  document.addEventListener('keydown', function (e) {
    if (mode !== 'run' || e.target.tagName === 'INPUT') return;
    var s = session;
    if (!s) return;
    if (e.key >= '1' && e.key <= '4' && !s.judged) {
      if (!el.rvChoices.querySelector('.rv-opt')) return;
      e.preventDefault();
      pick(+e.key - 1);
      submit();
      return;
    }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (s.judged) next(); else submit();
    }
  });

  // ------------------------------------------------------------ 启动

  // 背单词要的是「完整释义」，词库没到齐就先组不了卷 —— 两个词库都等一下
  function ready() {
    var W = window.CET6Word;
    if (!W) return Promise.resolve();
    return Promise.all([W.load(), W.loadAll()]);
  }

  readFilter();     // ?day= / ?set= / ?star=1 —— 从生词本的分组按钮或标记入口点进来

  function boot() {
    var t0 = Date.now();
    (function wait() {
      if (window.CET6Word || Date.now() - t0 > 4000) {
        ready().then(renderHome, renderHome);
        return;
      }
      setTimeout(wait, 50);
    })();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
