// 六级真题精读站 · 交互

function toggleTheme() {
  var cur = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
  var next = cur === 'dark' ? 'light' : 'dark';
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
  var dark = document.documentElement.dataset.theme === 'dark';
  var nozh = document.body.classList.contains('no-zh');
  var noans = document.body.classList.contains('hide-ans');
  setText('themeBtn', dark ? '☀' : '◐');
  setText('themeBtn2', dark ? '浅色' : '深色');
  setText('zhBtn', nozh ? '显示中文' : '中文对照');
  setText('ansBtn', noans ? '显示答案' : '隐藏答案');
  var b = document.getElementById('zhBtn'); if (b) b.classList.toggle('on', !nozh);
}

function setText(id, t) {
  var e = document.getElementById(id);
  if (e) e.textContent = t;
}

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
