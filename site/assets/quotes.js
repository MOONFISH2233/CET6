/* ==========================================================================
   每日一句（温柔文案）

   数据：assets/quotes.json（build_quotes.py 从 美工/*.md 解析出来的台词）
   用法：页面上放一个 <div class="qcard" data-quote="daily"></div>
     data-quote="daily"  按日期确定取句（同一天打开是同一句），带「换一句」按钮
     data-quote="day" data-day="12"  按第几天取句（打卡站用，每天一句不重复）
     data-quote="any"    随机取一句（空状态用）

   别的脚本（word.js）可以读 window.CET6Quotes.pick(i) / .random() 拿文案。
   ========================================================================== */

(function () {
  'use strict';

  var BASE = (function () {
    var s = document.currentScript && document.currentScript.src;
    if (!s) {
      var all = document.querySelectorAll('script[src*="quotes.js"]');
      s = all.length ? all[all.length - 1].src : '';
    }
    if (!s) return './';
    return s.replace(/assets\/quotes\.js.*$/, '');
  })();

  // 说话人头像（相对站点根；没有头像的作者就不显示）
  var AVATAR = {
    '温迪': 'assets/img/venti.png',
    '蒲熠星': 'assets/img/pyx.jpg',
    '孙路路': 'assets/img/sll.jpg'
  };
  var list = null, loading = null;

  function load() {
    if (list) return Promise.resolve(list);
    if (loading) return loading;
    loading = fetch(BASE + 'assets/quotes.json')
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (a) { list = a || []; return list; })
      .catch(function () { list = []; return list; });
    return loading;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function dayOfYear() {
    var d = new Date();
    var start = new Date(d.getFullYear(), 0, 0);
    return Math.floor((d - start) / 86400000);
  }

  function pick(i) {
    if (!list || !list.length) return null;
    var n = list.length;
    return list[((i % n) + n) % n];
  }

  function random() {
    if (!list || !list.length) return null;
    return list[Math.floor(Math.random() * list.length)];
  }

  // 卡片内文（不含外层 .qcard）
  function inner(q) {
    // 作者就是作品（原神）时不重复写《原神》
    var src = (q.s && q.s !== q.a) ? '《' + esc(q.s) + '》' : '';
    var av = AVATAR[q.a] ? '<img class="qav" src="' + esc(BASE + AVATAR[q.a]) + '" alt="">' : '';
    return '<div class="qtext">' + esc(q.t) + '</div>' +
           '<div class="qfoot">' + av +
             '<span class="qfrom">——' + esc(q.a) + (src ? ' · ' + src : '') + '</span>' +
           '</div>';
  }

  function paint(card, q) {
    var head = card.querySelector('.qhead') ? card.querySelector('.qhead').outerHTML : '';
    card.innerHTML = head + inner(q);
    card.classList.remove('qfade');
    void card.offsetWidth;          // 触发重排，让动画能重放
    card.classList.add('qfade');
  }

  function fillOne(card, a) {
    var mode = card.dataset.quote;
    var idx = mode === 'day' ? (+card.dataset.day || 0)
            : mode === 'daily' ? dayOfYear()
            : Math.floor(Math.random() * a.length);
    var q = pick(idx);
    if (!q) return;
    card.dataset.filled = '1';
    paint(card, q);
    // 事件委托：paint() 会重写 innerHTML（按钮元素被替换），绑在按钮上只能点一次
    card.onclick = function (e) {
      if (e.target && e.target.classList && e.target.classList.contains('qbtn')) {
        var nq = random();
        if (nq) paint(card, nq);
      }
    };
  }

  // 把页面上还没填过的 [data-quote] 卡片填上（打卡站重画今日卡片后会再调一次）
  function fill() {
    var cards = document.querySelectorAll('[data-quote]:not([data-filled])');
    if (!cards.length) return;
    load().then(function (a) {
      if (!a.length) return;
      Array.prototype.forEach.call(cards, function (card) { fillOne(card, a); });
    });
  }

  window.CET6Quotes = { load: load, pick: pick, random: random, fill: fill };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fill);
  } else {
    fill();
  }
})();
