// 六级真题精读站 · 交互

// 主题三档循环：浅色 → 深色 → 纯黑（OLED，夜里看更省电更不刺眼）
var THEMES = ['light', 'dark', 'oled'];

function curTheme() {
  var t = document.documentElement.dataset.theme;
  return THEMES.indexOf(t) >= 0 ? t : 'light';
}

function toggleTheme() {
  var next = THEMES[(THEMES.indexOf(curTheme()) + 1) % THEMES.length];
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('cet6-theme', next); } catch (e) {}
  syncButtons();
}

function toggleZh() {
  document.body.classList.toggle('no-zh');
  try {
    localStorage.setItem('cet6-nozh', document.body.classList.contains('no-zh') ? '1' : '0');
  } catch (e) {}
  syncButtons();
}

function toggleAns() {
  document.body.classList.toggle('hide-ans');
  try {
    localStorage.setItem('cet6-noans', document.body.classList.contains('hide-ans') ? '1' : '0');
  } catch (e) {}
  syncButtons();
}

function syncButtons() {
  var t = curTheme();
  var nozh = document.body.classList.contains('no-zh');
  var noans = document.body.classList.contains('hide-ans');
  setText('themeBtn', t === 'light' ? '◐' : (t === 'dark' ? '◑' : '☀'));
  setText('themeBtn2', t === 'light' ? '深色' : (t === 'dark' ? '纯黑' : '浅色'));
  setText('zhBtn', nozh ? '显示中文' : '中文对照');
  setText('ansBtn', noans ? '显示答案' : '隐藏答案');
  var b = document.getElementById('zhBtn'); if (b) b.classList.toggle('on', !nozh);
}

function setText(id, t) {
  var e = document.getElementById(id);
  if (e) e.textContent = t;
}

// ---------------------------------------------------------------- 听力音频
// 播放器就一个 <audio>（原生控件），页面上所有「听这题」「跳到第 N 篇」都是在设它的
// currentTime：比每处塞一个播放器省事，也不会好几个播放器一起响。
// 时间点还可以带在地址里（#t=123），分享/刷新都能回到那句话。
(function () {
  var player = null;
  var pending = null;       // 音频还没就绪前记下想跳的时间，等 loadedmetadata 再跳

  function seek(t, play) {
    if (!player) return;
    player.currentTime = t;
    if (play) { var p = player.play(); if (p && p.catch) p.catch(function () {}); }
  }

  // 各处的入口：听力页的胶囊、每题旁的「听这题」、打卡站的播放按钮
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('[data-aud]') : null;
    if (!el) return;
    var t = parseFloat(el.dataset.aud);
    if (isNaN(t)) return;
    e.preventDefault();                              // A 标签也别真跳走
    // 先把地址记下（分享/刷新能回到这句），再跳；音频出问题也不影响记地址
    try { history.replaceState(null, '', '#t=' + t); } catch (err) {}
    seek(t, true);
  });

  // 落地时就带 #t=… 的：滚到播放器、跳过去、自动播一遍
  function fromHash() {
    var m = (location.hash || '').match(/t=([\d.]+)/);
    if (!m || !player) return;
    var t = parseFloat(m[1]);
    var card = document.getElementById('audCard');
    if (card && card.scrollIntoView) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    // ⚠️ 手机上用 #t= 那种片段跳转，音频元素自己是不认的（它只认媒体片段），
    //    这里手动设 currentTime；自动播放在部分浏览器要用户手势，失败了就静静等着
    if (player.readyState === 0) { pending = t; player.load(); }
    else seek(t, true);
  }

  window.addEventListener('DOMContentLoaded', function () {
    player = document.getElementById('audPlayer');
    if (!player) return;
    player.addEventListener('loadedmetadata', function () {
      if (pending === null) return;
      var t = pending;
      pending = null;
      seek(t, true);
    });
    if (location.hash) fromHash();
  });
})();

// 初始化：恢复用户偏好
(function () {
  try {
    var th = localStorage.getItem('cet6-theme');
    if (th) document.documentElement.dataset.theme = th;
    else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      document.documentElement.dataset.theme = 'dark';
    if (localStorage.getItem('cet6-nozh') === '1') document.body.classList.add('no-zh');
    // 答案默认隐藏：只在有答案的页面（body 初始就带 hide-ans）
    if (localStorage.getItem('cet6-noans') === '0') document.body.classList.remove('hide-ans');
  } catch (e) {}
})();

// 键盘快捷键
 document.addEventListener('keydown', function (e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'a' || e.key === 'A') toggleAns();
  if (e.key === 'z' || e.key === 'Z') toggleZh();
  if (e.key === 'd' || e.key === 'D') toggleTheme();
});

window.addEventListener('DOMContentLoaded', syncButtons);
