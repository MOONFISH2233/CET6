/* ==========================================================================
   点词查义 + 收藏（生词本 / 错题本 / 句子）+ 我的学习页 + 重点词页

   数据：
     /cet6/dict.json         全局词库（含 CEFR / 词性释义 / 频次）
     /cet6/hfw/<set>.json    该套的重点词表，每条带 mods（出自哪几个模块页）
   存储：localStorage（本机，不上传）
     cet6:vocab    生词本 [{w, gloss, cefr, src, t}]   src = "2022-06-1/reading1"
     cet6:wrong    错题本 [{set, mod, no, my, ans, t}]
     cet6:sents    句子收藏 [{set, en, zh, t}]          set = "2022-06-1/reading1"
   ⚠️ 键名与记录结构是和打卡站（/cet6/plan/）约定好的，改字段会打断互通。
   ⚠️ 写入方只有本文件；quiz.js 也写 cet6:wrong，两个镜像互相覆盖是既有风险，
      所以这里每次渲染前重新 load()，不要缓存太久。
   ========================================================================== */

(function () {
  'use strict';

  // 站点可能部署在子目录（如 /cet6/），所以用相对 assets/ 的路径推算根
  var ASSET_BASE = (function () {
    var s = document.currentScript && document.currentScript.src;
    if (!s) {
      var all = document.querySelectorAll('script[src*="word.js"]');
      s = all.length ? all[all.length - 1].src : '';
    }
    if (!s) return './';
    return s.replace(/assets\/word\.js.*$/, '');
  })();
  var DICT_URL = ASSET_BASE + 'dict.json';
  var DICT_ALL_URL = ASSET_BASE + 'dict_all.json';
  var HFW_BASE = ASSET_BASE + 'hfw/';
  var LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

  var dict = null;          // {words:{}, forms:{}}  懒笔记来的核心词库（带 CEFR/真题频次）
  var dictAll = null;       // {lemmas:{}, forms:{}}  ECDICT 裁出来的兜底词库（懒加载）
  var hfw = null;           // 本篇重点词（loadHfw 后已按模块过滤）
  var dictLoading = null;
  var dictAllLoading = null;

  // ------------------------------------------------------------ 存储

  function load(key, def) {
    try {
      var s = localStorage.getItem(key);
      return s ? JSON.parse(s) : def;
    } catch (e) { return def; }
  }

  function save(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
  }

  var vocab = load('cet6:vocab', []);
  var wrong = load('cet6:wrong', []);
  var sents = load('cet6:sents', []);
  var onVocabChange = null;   // 我的学习页注册的回调：收藏变了重画列表

  function pageId() {
    // 从 URL 推出 "2022-06-1/reading1"（兼容子目录部署）
    var m = location.pathname.match(/\/p\/([^/]+)\/([^/.]+)\.html/);
    return m ? m[1] + '/' + m[2] : '';
  }

  function setId() {
    var pid = pageId();
    return pid ? pid.split('/')[0] : '';
  }

  function currentMod() {
    var pid = pageId();
    return pid ? (pid.split('/')[1] || '') : '';
  }

  // ------------------------------------------------------------ 词库

  function loadDict() {
    if (dict) return Promise.resolve(dict);
    if (dictLoading) return dictLoading;
    dictLoading = fetch(DICT_URL)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { dict = d; return d; })
      .catch(function () { return null; });
    return dictLoading;
  }

  function loadHfw() {
    var set = setId();
    if (!set) return Promise.resolve([]);
    return fetch(HFW_BASE + set + '.json')
      .then(function (r) { return r.ok ? r.json() : []; })
      .catch(function () { return []; })
      .then(function (list) {
        // 只留本篇出现的词；旧数据没有 mods 时不过滤（fail-open）
        var mod = currentMod();
        hfw = (list || []).filter(function (w) {
          return !w.mods || w.mods.indexOf(mod) >= 0;
        });
        return hfw;
      });
  }

  // 查词：先精确，再词形还原
  function lookup(word) {
    if (!dict) return null;
    var w = word.toLowerCase().replace(/[^a-z'-]/g, '');
    if (!w) return null;
    if (dict.words[w]) return { key: w, data: dict.words[w] };
    // 词形还原
    var cands = dict.forms && dict.forms[w];
    if (cands && cands.length) {
      var k = cands[0];
      return { key: k, data: dict.words[k], inflected: true };
    }
    return null;
  }

  // ------------------------------------------------------------ 弹窗

  var pop = null;

  function ensurePop() {
    if (pop) return pop;
    pop = document.createElement('div');
    pop.className = 'wpop';
    pop.hidden = true;
    document.body.appendChild(pop);
    document.addEventListener('click', function (e) {
      if (pop.hidden) return;
      if (pop.contains(e.target)) return;
      if (e.target.classList && (e.target.classList.contains('w') ||
          e.target.classList.contains('hfw-chip') ||
          e.target.classList.contains('vw'))) return;
      hidePop();
    });
    window.addEventListener('scroll', function () { hidePop(); }, { passive: true });
    return pop;
  }

  function hidePop() {
    if (pop) pop.hidden = true;
  }

  function showPop(el, html) {
    var p = ensurePop();
    p.innerHTML = html;
    p.hidden = false;
    var r = el.getBoundingClientRect();
    var pw = Math.min(320, window.innerWidth - 24);
    p.style.width = pw + 'px';
    var left = Math.min(Math.max(8, r.left + r.width / 2 - pw / 2), window.innerWidth - pw - 8);
    var top = r.bottom + 6 + window.scrollY;
    p.style.left = left + 'px';
    p.style.top = top + 'px';
  }

  // ------------------------------------------------------------ 生词本读写

  function vocabHas(w) {
    return vocab.some(function (x) { return x.w === w; });
  }

  function addVocab(word, data) {
    if (vocabHas(word)) return false;
    vocab.unshift({
      w: word,
      gloss: data ? (data.gloss || '') : '',
      cefr: data ? (data.cefr || '') : '',
      src: pageId(),
      t: Date.now()
    });
    save('cet6:vocab', vocab);
    return true;
  }

  function delVocab(w) {
    vocab = vocab.filter(function (x) { return x.w !== w; });
    save('cet6:vocab', vocab);
  }

  // 加入 / 移出，并把页面上所有相关标记刷新一遍
  // data 可选：扩展词库查到的释义（{gloss, cefr}），核心词库命中时不用传
  function toggleVocab(word, data) {
    if (vocabHas(word)) {
      delVocab(word);
    } else {
      var hit = lookup(word);
      addVocab(word, data || (hit ? hit.data : null));
    }
    syncVocabUI();
    if (onVocabChange) onVocabChange();   // 我的学习页据此重画列表
    return vocabHas(word);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ------------------------------------------------------------ 共用小工具

  // "2023-06-1/reading1" -> {href, text}
  function pageLink(src) {
    var labels = window.CET6_LABELS || {};
    var parts = String(src || '').split('/');
    var set = parts[0] || '', mod = parts[1] || '';
    var setTxt = (labels.sets && labels.sets[set]) || set;
    var modTxt = (labels.mods && labels.mods[mod]) || mod;
    var text = [setTxt, modTxt].filter(Boolean).join(' · ');
    return {
      href: (set && mod) ? ASSET_BASE + 'p/' + set + '/' + mod + '.html' : '',
      text: text
    };
  }

  function srcHTML(src) {
    var l = pageLink(src);
    if (!l.text) return '从重点词页收录';
    return l.href ? '<a href="' + esc(l.href) + '">' + esc(l.text) + '</a>' : esc(l.text);
  }

  function fmtTime(t) {
    if (!t) return '';
    var d = Math.floor((Date.now() - t) / 86400000);
    if (d <= 0) return '今天';
    if (d === 1) return '昨天';
    if (d < 30) return d + ' 天前';
    var dt = new Date(t);
    return dt.getFullYear() + '-' +
           ('0' + (dt.getMonth() + 1)).slice(-2) + '-' + ('0' + dt.getDate()).slice(-2);
  }

  // 兼容历史坏记录：no 可能是 "第 26 空"，ans 可能是 "A) aesthetically副词"
  function noNum(v) {
    var m = String(v == null ? '' : v).match(/\d+/);
    return m ? m[0] : '';
  }

  function ansLetter(v) {
    var m = String(v == null ? '' : v).match(/[A-Za-z]/);
    return m ? m[0].toUpperCase() : '';
  }

  // ------------------------------------------------------------ 兜底词库
  // dict.json 只有懒笔记的 2062 个高频词，读文章时大量基础词（the/children/made…）查不到。
  // dict_all.json 是构建期从 ECDICT（MIT）裁出来的兜底词库，只在没命中时才懒加载。

  function loadDictAll() {
    if (dictAll) return Promise.resolve(dictAll);
    if (dictAllLoading) return dictAllLoading;
    dictAllLoading = fetch(DICT_ALL_URL)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { dictAll = d; return d; })
      .catch(function () { return null; });
    return dictAllLoading;
  }

  // ECDICT 的 tag 是一串（zk gk cet4 cet6 ky ielts…），只显示最相关的一个
  var TAG_LABEL = { cet6: 'CET6', cet4: 'CET4', ky: '考研', toefl: 'TOEFL',
                    ielts: 'IELTS', gre: 'GRE', gk: '高考', zk: '中考' };
  var TAG_ORDER = ['cet6', 'cet4', 'ky', 'toefl', 'ielts', 'gre', 'gk', 'zk'];

  function bestTag(s) {
    var parts = String(s || '').split(/\s+/);
    for (var i = 0; i < TAG_ORDER.length; i++) {
      if (parts.indexOf(TAG_ORDER[i]) >= 0) return TAG_LABEL[TAG_ORDER[i]];
    }
    return '';
  }

  function lookupAll(word) {
    if (!dictAll) return null;
    var w = String(word).toLowerCase().replace(/[^a-z'-]/g, '');
    if (!w) return null;
    var L = dictAll.lemmas || {}, F = dictAll.forms || {}, T = dictAll.tags || {};
    var FT = dictAll.ftypes || {};
    if (L[w]) return { key: w, gloss: L[w], tag: bestTag(T[w]) };
    var f = F[w];
    if (f && L[f]) return { key: f, gloss: L[f], tag: bestTag(T[f]), inflected: true, ftype: FT[w] || "" };
    var f2 = f ? F[f] : null;            // 两跳：children's -> children -> child
    if (f2 && L[f2]) return { key: f2, gloss: L[f2], tag: bestTag(T[f2]), inflected: true, ftype: FT[f] || "" };
    return null;
  }

  // ------------------------------------------------------------ 查词弹窗

  function openWordPop(el, word) {
    loadDict().then(function () {
      var hit = lookup(word);
      if (hit) {
        renderPop(el, word, {
          key: hit.key, gloss: hit.data.gloss, cefr: hit.data.cefr,
          exam: hit.data.exam, papers: (hit.data.papers || []).length,
          inflected: hit.inflected
        });
        return;
      }
      loadDictAll().then(function (d) {
        var ext = d ? lookupAll(word) : null;
        renderPop(el, word, ext
          ? { key: ext.key, gloss: ext.gloss, cefr: ext.tag, inflected: ext.inflected,
              ftype: ext.ftype, ext: true }
          : { key: String(word).toLowerCase() });
      });
    });
  }

  function renderPop(el, word, res) {
    var key = res.key;
    var inVocab = vocabHas(key);
    var h = [];
    h.push('<div class="wpop-head"><span class="wpop-word">' + esc(word) + '</span>');
    if (res.cefr) h.push('<span class="wpop-cefr">' + esc(res.cefr) + '</span>');
    if (res.ext) h.push('<span class="wpop-ext">扩展词库</span>');
    h.push('<button class="wpop-close" aria-label="关闭">×</button></div>');

    if (res.gloss) {
      h.push('<div class="wpop-gloss">' + esc(res.gloss) + '</div>');
      if (res.inflected && res.key !== String(word).toLowerCase()) {
        // 说清是什么形式：made → make 的过去式/过去分词
        h.push('<div class="wpop-note">' +
               (res.ftype ? esc(res.ftype) + ' → ' : '原形：') +
               '<b>' + esc(res.key) + '</b></div>');
      }
      if (res.exam) {
        h.push('<div class="wpop-note">真题出现 ' + res.exam + ' 句 · 收录于 ' +
               res.papers + ' 套</div>');
      }
    } else {
      h.push('<div class="wpop-gloss wpop-miss">词库未收录 —— 多半是专有名词（人名、地名、机构名）' +
             '或新造词。</div>');
    }

    h.push('<div class="wpop-acts">');
    h.push('<button class="wpop-act ' + (inVocab ? 'on' : '') + '" data-act="vocab">' +
           (inVocab ? '✓ 已在生词本' : '＋ 加入生词本') + '</button>');
    // 只有文章页才谈得上「这个句子」：重点词页/我的学习页没有正文
    if (pageId()) {
      h.push('<button class="wpop-act" data-act="sentence">记这个句子</button>');
    }
    h.push('</div>');

    // 本篇重点词标记（hfw 已在 loadHfw 里按本篇过滤过）
    if (hfw && hfw.length) {
      var isKey = hfw.some(function (x) { return x.word.toLowerCase() === key; });
      if (isKey) h.push('<div class="wpop-note wpop-key">★ 本篇重点词</div>');
    }

    showPop(el, h.join(''));

    pop.querySelector('.wpop-close').onclick = hidePop;
    var vb = pop.querySelector('[data-act="vocab"]');
    if (vb) vb.onclick = function () {
      var on = toggleVocab(key, res.gloss ? { gloss: res.gloss, cefr: res.cefr || '' } : null);
      vb.classList.toggle('on', on);
      vb.textContent = on ? '✓ 已在生词本' : '＋ 加入生词本';
    };
    var sb = pop.querySelector('[data-act="sentence"]');
    if (sb) sb.onclick = function () {
      var p = el.closest('.para, .tr-line, .q, .sent');
      var en = '', zh = '';
      if (p) {
        var e1 = p.querySelector('.en');
        var z1 = p.querySelector('.zh');
        en = e1 ? e1.textContent.trim() : '';
        zh = z1 ? z1.textContent.trim() : '';
      }
      sents.unshift({ set: pageId(), en: en || el.textContent, zh: zh, t: Date.now() });
      save('cet6:sents', sents);
      sb.textContent = '✓ 已收藏';
      sb.classList.add('on');
      updateCounts();
    };
  }

  function onClick(e) {
    var el = e.target;
    if (!el.classList || !el.classList.contains('w')) return;
    e.stopPropagation();
    openWordPop(el, el.dataset.w || el.textContent);
  }

  // 页面上所有「收了没」的视觉标记，一次刷新
  function syncVocabUI() {
    var has = {};
    vocab.forEach(function (v) { has[v.w] = 1; });
    document.querySelectorAll('.w[data-w], .hfw-chip[data-w], .vw[data-w]').forEach(function (el) {
      el.classList.toggle('marked', !!has[el.dataset.w]);
    });
    document.querySelectorAll('.vadd[data-w]').forEach(function (b) {
      var on = !!has[b.dataset.w];
      b.classList.toggle('on', on);
      b.textContent = on ? '✓ 已在生词本' : '＋ 生词本';
    });
    renderNotes();
    updateCounts();
  }

  // 收进生词本的词，在它所在的段落下面留一行小注（像在旁边做笔记）
  function renderNotes() {
    if (!pageId()) return;
    var gloss = {};
    vocab.forEach(function (v) { gloss[v.w] = v.gloss || ''; });
    document.querySelectorAll('.para, .tr-line, .sent, .q').forEach(function (blk) {
      var seen = {}, words = [];
      blk.querySelectorAll('.w.marked').forEach(function (el) {
        var w = el.dataset.w;
        if (!w || seen[w]) return;
        seen[w] = 1;
        words.push('<b>' + esc(w) + '</b>' + (gloss[w] ? ' ' + esc(gloss[w]) : ''));
      });
      var box = blk.querySelector(':scope > .wnotes');
      if (!words.length) { if (box) box.remove(); return; }
      if (!box) {
        box = document.createElement('div');
        box.className = 'wnotes';
        blk.appendChild(box);
      }
      box.innerHTML = '<span class="wnotes-h">生词</span>' +
                      words.join('<span class="sep">·</span>');
    });
  }

  // ------------------------------------------------------------ 分词包装

  var WORD_RE = /[A-Za-z][A-Za-z'-]*/g;

  function wrapWords(root) {
    if (!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !/[A-Za-z]/.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
        var p = n.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        var tag = p.nodeName.toLowerCase();
        if (tag === 'script' || tag === 'style' || tag === 'mark') return NodeFilter.FILTER_REJECT;
        if (p.classList && (p.classList.contains('w') || p.classList.contains('wpop'))) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function (node) {
      var text = node.nodeValue;
      if (!/[A-Za-z]/.test(text)) return;
      var frag = document.createDocumentFragment();
      var last = 0, m;
      WORD_RE.lastIndex = 0;
      while ((m = WORD_RE.exec(text))) {
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var sp = document.createElement('span');
        sp.className = 'w';
        sp.dataset.w = m[0].toLowerCase();
        sp.textContent = m[0];
        frag.appendChild(sp);
        last = m.index + m[0].length;
      }
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      if (node.parentNode) node.parentNode.replaceChild(frag, node);
    });
  }

  // ------------------------------------------------------------ 计数

  function updateCounts() {
    var a = document.getElementById('vocabCount'); if (a) a.textContent = vocab.length;
    var b = document.getElementById('cntVocab'); if (b) b.textContent = vocab.length;
    var c = document.getElementById('cntWrong'); if (c) c.textContent = wrong.length;
    var d = document.getElementById('cntSents'); if (d) d.textContent = sents.length;
  }

  // ------------------------------------------------------------ 错题标记按钮

  function addWrongButtons() {
    if (!/\/(listening|reading1|reading2|longreading|cloze)\.html/.test(location.pathname)) return;
    document.querySelectorAll('.q').forEach(function (q) {
      var badge = q.querySelector('.ansbadge');
      if (!badge) return;
      // 优先用 gen_site 写好的 data-*，退回解析徽标文本
      var no = q.dataset.qno || (q.querySelector('.q-no') ? q.querySelector('.q-no').textContent.trim() : '');
      var ans = q.dataset.answer || badge.textContent.trim().split(/[（(\s]/)[0];
      var btn = document.createElement('button');
      btn.className = 'wrongbtn';
      btn.type = 'button';
      btn.textContent = '我做错了';
      btn.onclick = function () {
        var my = prompt('你选的是哪个？（填 A/B/C/D，可留空）', '');
        var pid = pageId();
        wrong = load('cet6:wrong', []);
        wrong.unshift({
          set: pid.split('/')[0], mod: pid.split('/')[1] || '',
          no: no, my: (my || '').toUpperCase().slice(0, 1), ans: ans, t: Date.now()
        });
        save('cet6:wrong', wrong);
        btn.textContent = '✓ 已记入错题本';
        btn.classList.add('on');
        updateCounts();
      };
      badge.parentNode.insertBefore(btn, badge.nextSibling);
    });
  }

  // ------------------------------------------------------------ 模块页重点词块

  function renderHfw() {
    var box = document.getElementById('hfwBox');
    if (!box) return;
    var list = hfw || [];
    if (!list.length) { box.hidden = true; box.open = false; return; }

    var by = {};
    list.forEach(function (w) { by[w.cefr] = (by[w.cefr] || 0) + 1; });
    var sum = document.getElementById('hfwSum');
    if (sum) {
      var parts = LEVELS.filter(function (l) { return by[l]; })
                        .map(function (l) { return l + ' ' + by[l]; });
      sum.textContent = '本篇 ' + list.length + ' 词 · ' + parts.join(' · ');
    }

    var box2 = document.getElementById('hfwList');
    if (box2) {
      box2.innerHTML = list.map(function (w) {
        return '<span class="hfw-chip" data-w="' + esc(w.word.toLowerCase()) + '">' +
               esc(w.word) + '<i class="hfw-c">' + esc(w.cefr) + '</i></span>';
      }).join('');
      box2.querySelectorAll('.hfw-chip').forEach(function (c) {
        c.onclick = function () { openWordPop(c, c.dataset.w); };
      });
    }
    box.hidden = false;   // 仍是收起状态（没有 open），点一下才展开
  }

  // ------------------------------------------------------------ 重点词页

  var HFW_PAGE_LIMIT = 120;

  function initHfwPage() {
    var root = document.getElementById('hfwPage');
    if (!root) return;
    var searchEl = document.getElementById('hfwSearch');
    var moreBtn = document.getElementById('hfwMore');
    var totalEl = document.getElementById('hfwTotal');
    var levelsEl = document.getElementById('hfwLevels');
    var lv = '', q = '', shown = HFW_PAGE_LIMIT, all = [], timer = null;

    loadDict().then(function (d) {
      if (!d || !d.words) { root.innerHTML = '<p class="vempty">词库加载失败，刷新重试。</p>'; return; }
      all = Object.keys(d.words).map(function (k) {
        var w = d.words[k];
        return {
          w: k, cefr: w.cefr || '', gloss: w.gloss || '',
          freq: w.freq || 0, exam: w.exam || 0,
          papers: (w.papers || []).length
        };
      }).sort(function (a, b) { return b.freq - a.freq || (a.w < b.w ? -1 : 1); });
      render();
    });

    function matched() {
      var qq = q.toLowerCase();
      return all.filter(function (x) {
        if (lv && x.cefr !== lv) return false;
        if (!qq) return true;
        return x.w.indexOf(qq) >= 0 || x.gloss.toLowerCase().indexOf(qq) >= 0;
      });
    }

    function row(x) {
      return '<div class="vitem">' +
        '<div class="vitem-main">' +
          '<b class="vw" data-w="' + esc(x.w) + '">' + esc(x.w) + '</b>' +
          (x.cefr ? '<span class="vcefr">' + esc(x.cefr) + '</span>' : '') +
          '<span class="vgloss">' + esc(x.gloss || '—') + '</span>' +
          '<div class="vitem-sub">出现 ' + x.papers + ' 套 · 真题 ' + x.exam + ' 句</div>' +
        '</div>' +
        '<button class="vadd" data-w="' + esc(x.w) + '">＋ 生词本</button>' +
      '</div>';
    }

    function render() {
      var list = matched();
      var slice = list.slice(0, shown);
      root.innerHTML = slice.length ? slice.map(row).join('')
                                    : '<p class="vempty">没有匹配的词。</p>';
      if (totalEl) {
        totalEl.textContent = '共 ' + list.length + ' 词' +
          (list.length > slice.length ? ' · 已显示 ' + slice.length : '');
      }
      if (moreBtn) {
        var rest = list.length - slice.length;
        moreBtn.hidden = rest <= 0;
        moreBtn.textContent = '加载更多（还剩 ' + rest + '）';
      }
      syncVocabUI();
    }

    root.onclick = function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains('vadd')) { toggleVocab(t.dataset.w); return; }
      if (t.classList && t.classList.contains('vw') && t.dataset.w) {
        openWordPop(t, t.dataset.w);
      }
    };

    if (levelsEl) levelsEl.querySelectorAll('.lvchip').forEach(function (b) {
      b.onclick = function () {
        lv = b.dataset.lv || '';
        levelsEl.querySelectorAll('.lvchip').forEach(function (x) {
          x.classList.toggle('on', x === b);
        });
        shown = HFW_PAGE_LIMIT;
        render();
      };
    });

    if (moreBtn) moreBtn.onclick = function () { shown += HFW_PAGE_LIMIT * 2; render(); };

    if (searchEl) searchEl.oninput = function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        q = searchEl.value.trim();
        shown = HFW_PAGE_LIMIT;
        render();
      }, 120);
    };
  }

  // ------------------------------------------------------------ 我的学习页

  function initMePage() {
    var root = document.getElementById('meRoot');
    var list = document.getElementById('meList');
    if (!root || !list) return;
    var tabsEl = document.querySelector('.tabs');
    var searchEl = document.getElementById('meSearch');
    var cur = 'vocab', q = '';

    var EMPTY = {
      vocab: '还没有生词。读文章时点单词，再点「加入生词本」；在重点词页也能一键收词。',
      wrong: '还没有错题。做题页提交后会记下来，也可以点每题旁的「我做错了」。',
      sents: '还没有收藏句子。读文章时点单词，再点「记这个句子」。'
    };

    // 空状态：提示 + 一句温柔台词（台词由 quotes.js 提供，取哪句按标签名固定）
    function emptyHTML(tab) {
      var h = '<p class="vempty">' + EMPTY[tab] + '</p>';
      var q = (window.CET6Quotes && window.CET6Quotes.pick) ? window.CET6Quotes.pick(tabHash(tab)) : null;
      if (q) {
        h += '<p class="vempty-quote">「' + esc(q.t) + '」<br>——' + esc(q.a) +
             ((q.s && q.s !== q.a) ? ' ·《' + esc(q.s) + '》' : '') + '</p>';
      }
      return h;
    }

    function tabHash(s) {
      var n = 0;
      for (var i = 0; i < s.length; i++) n = (n * 31 + s.charCodeAt(i)) % 9973;
      return n;
    }

    function vocabRow(v) {
      return '<div class="vitem">' +
        '<div class="vitem-main">' +
          '<b class="vw" data-w="' + esc(v.w) + '">' + esc(v.w) + '</b>' +
          (v.cefr ? '<span class="vcefr">' + esc(v.cefr) + '</span>' : '') +
          '<span class="vgloss">' + esc(v.gloss || '—') + '</span>' +
          '<div class="vitem-sub">' + srcHTML(v.src) + ' · ' + esc(fmtTime(v.t)) + '</div>' +
        '</div>' +
        '<button class="vdel" data-del="vocab" data-w="' + esc(v.w) + '">删</button>' +
      '</div>';
    }

    function wrongRow(v, i) {
      var no = noNum(v.no), ans = ansLetter(v.ans), my = ansLetter(v.my);
      var l = pageLink((v.set || '') + '/' + (v.mod || ''));
      var href = l.href ? l.href + (no ? '#q' + no : '') : '';
      return '<div class="vitem">' +
        '<div class="vitem-main">' +
          '<b class="vw">第 ' + esc(no || '?') + ' 题</b>' +
          '<span class="vgloss">' +
            (my ? '我选 <b class="vbad">' + esc(my) + '</b> · ' : '') +
            '正确 <b class="vok">' + esc(ans || '?') + '</b>' +
          '</span>' +
          '<div class="vitem-sub">' +
            (href ? '<a href="' + esc(href) + '">' + esc(l.text) + ' · 去重做</a>' : esc(l.text)) +
            ' · ' + esc(fmtTime(v.t)) +
          '</div>' +
        '</div>' +
        '<button class="vdel" data-del="wrong" data-i="' + i + '">删</button>' +
      '</div>';
    }

    function sentRow(v, i) {
      var l = pageLink(v.set);
      return '<div class="vitem">' +
        '<div class="vitem-main">' +
          '<div class="me-en">' + esc(v.en || '') + '</div>' +
          (v.zh ? '<div class="me-zh">' + esc(v.zh) + '</div>' : '') +
          '<div class="vitem-sub">' +
            (l.href ? '<a href="' + esc(l.href) + '">' + esc(l.text) + '</a>' : esc(l.text)) +
            ' · ' + esc(fmtTime(v.t)) +
          '</div>' +
        '</div>' +
        '<button class="vdel" data-del="sents" data-i="' + i + '">删</button>' +
      '</div>';
    }

    function render() {
      // 每次都重读：别的标签页改了数据，别拿旧副本把它盖回去
      vocab = load('cet6:vocab', []);
      wrong = load('cet6:wrong', []);
      sents = load('cet6:sents', []);

      var qq = q.toLowerCase(), h = [];
      if (cur === 'vocab') {
        var vs = vocab.filter(function (v) {
          return !qq || String(v.w).toLowerCase().indexOf(qq) >= 0 ||
                 String(v.gloss || '').toLowerCase().indexOf(qq) >= 0;
        });
        vs.forEach(function (v) { h.push(vocabRow(v)); });
      } else if (cur === 'wrong') {
        var ws = wrong.filter(function (v) {
          return !qq || (String(v.set || '') + '/' + String(v.mod || '') + '/' + String(v.no || ''))
                 .toLowerCase().indexOf(qq) >= 0;
        });
        ws.forEach(function (v) { h.push(wrongRow(v, wrong.indexOf(v))); });
      } else {
        var ss = sents.filter(function (v) {
          return !qq || String(v.en || '').toLowerCase().indexOf(qq) >= 0 ||
                 String(v.zh || '').indexOf(qq) >= 0;
        });
        ss.forEach(function (v) { h.push(sentRow(v, sents.indexOf(v))); });
      }

      list.innerHTML = h.length ? h.join('') : emptyHTML(cur);
      if (searchEl) searchEl.placeholder = cur === 'vocab' ? '搜索生词或释义…'
        : (cur === 'wrong' ? '搜索考期或题型…' : '搜索句子…');
      updateCounts();
    }

    if (tabsEl) tabsEl.querySelectorAll('.tab').forEach(function (b) {
      b.onclick = function () {
        cur = b.dataset.tab;
        tabsEl.querySelectorAll('.tab').forEach(function (x) {
          x.classList.toggle('on', x === b);
        });
        q = '';
        if (searchEl) searchEl.value = '';
        render();
      };
    });

    root.onclick = function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains('vdel')) {
        var kind = t.dataset.del, i = +t.dataset.i;
        if (kind === 'vocab') delVocab(t.dataset.w);
        else if (kind === 'wrong') { wrong.splice(i, 1); save('cet6:wrong', wrong); }
        else { sents.splice(i, 1); save('cet6:sents', sents); }
        render();
        return;
      }
      if (t.classList && t.classList.contains('vw') && t.dataset.w) {
        openWordPop(t, t.dataset.w);
      }
    };

    var exp = document.getElementById('meExport');
    if (exp) exp.onclick = function () {
      render();
      var data = { vocab: vocab, wrong: wrong, sents: sents,
                   exported: new Date().toISOString().slice(0, 10) };
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'cet6-生词错题-' + data.exported + '.json';
      a.click();
    };

    var clr = document.getElementById('meClear');
    if (clr) clr.onclick = function () {
      var name = cur === 'vocab' ? '生词本' : (cur === 'wrong' ? '错题本' : '句子收藏');
      if (!confirm('清空' + name + '？不可恢复。')) return;
      if (cur === 'vocab') { vocab = []; save('cet6:vocab', vocab); }
      else if (cur === 'wrong') { wrong = []; save('cet6:wrong', wrong); }
      else { sents = []; save('cet6:sents', sents); }
      render();
    };

    if (searchEl) searchEl.oninput = function () { q = searchEl.value.trim(); render(); };

    onVocabChange = render;
    render();
    // 空状态那句台词要等 quotes.json 到位，到了再重画一次
    if (window.CET6Quotes) {
      window.CET6Quotes.load().then(function (a) { if (a && a.length) render(); });
    }
  }

  // ------------------------------------------------------------ 初始化

  var inited = false;

  function init() {
    if (inited) return;
    inited = true;

    // 我的学习页：只渲染收藏列表
    if (document.getElementById('meRoot')) { initMePage(); return; }

    // 重点词页：渲染全局词表
    if (document.getElementById('hfwPage')) { initHfwPage(); return; }

    document.addEventListener('click', onClick);

    // 只包正文区域，避免把按钮/导航也切开
    document.querySelectorAll('.card, .zhblock, .enblock').forEach(wrapWords);

    loadHfw().then(function () { renderHfw(); syncVocabUI(); });
    loadDict();
    addWrongButtons();
    updateCounts();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
