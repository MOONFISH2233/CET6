# -*- coding: utf-8 -*-
"""打卡站页面模板。占位符 __DATA__ 由 gen_plan.py 注入 plan JSON。"""

PAGE_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>六级 62 天备考计划</title>
<link rel="stylesheet" href="../assets/style.css">
<link rel="icon" href="../assets/img/favicon.png">
<link rel="apple-touch-icon" href="../assets/img/logo.png">
<style>
.plan-hero{text-align:center;padding:26px 16px 18px}
.plan-hero h1{font-size:24px;margin:0 0 6px}
.countdown{font-size:40px;font-weight:700;line-height:1.1;color:var(--accent)}
.countdown small{font-size:14px;font-weight:400;color:var(--fg-soft);margin-left:6px}
.pbar{height:10px;border-radius:6px;background:var(--line);overflow:hidden;margin:14px 0 6px}
.pbar i{display:block;height:100%;background:var(--accent);transition:width .3s}
.pmeta{font-size:13px;color:var(--fg-soft)}
.today{border:2px solid var(--accent)}
.today .th{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.today .th b{font-size:17px}
.big{font-size:19px;font-weight:700;margin:10px 0 4px}
.big a{text-decoration:none}
.dsteps{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px}
.dstep{font-size:12.5px;padding:4px 9px;border:1px solid var(--line);border-radius:20px;cursor:pointer;user-select:none}
.dstep.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.wk{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;margin-top:10px}
.wk div{aspect-ratio:1;border:1px solid var(--line);border-radius:7px;display:flex;
  flex-direction:column;align-items:center;justify-content:center;font-size:11px;cursor:pointer;padding:2px}
.wk div.p1{border-color:#5b8def}
.wk div.p2{border-color:#e0a33a}
.wk div.p3{border-color:#d4576a}
.wk div.done{background:var(--accent);color:#fff}
.wk div.today{outline:2px solid var(--accent);outline-offset:1px}
.wk div.future{opacity:.45}
.daylist{margin-top:16px}
.dayrow{border:1px solid var(--line);border-radius:9px;padding:11px 13px;margin-bottom:8px}
.dayrow .dh{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.dayrow .dh b{font-size:14.5px}
.dayrow .dt{font-size:12px;color:var(--fg-faint)}
.dayrow .body{margin-top:7px;font-size:13.5px;line-height:1.75}
.dayrow .body a{text-decoration:none;border-bottom:1px dashed var(--accent)}
.tagx{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--line);margin-right:5px}
.note{font-size:12.5px;color:var(--fg-soft);margin-top:6px}
.ghost{background:none;border:1px solid var(--line);color:inherit;border-radius:7px;
  padding:5px 11px;font-size:12.5px;cursor:pointer}
.vok{color:#2f9e44;font-weight:600}
.rowacts{display:flex;gap:7px;align-items:center;margin-top:8px;flex-wrap:wrap}
.phase-card{border-left:3px solid var(--line);padding-left:12px;margin:14px 0}
.phase-card.p1{border-color:#5b8def}
.phase-card.p2{border-color:#e0a33a}
.phase-card.p3{border-color:#d4576a}
</style>
</head>
<body>
<header class="site">
  <div class="site-inner">
    <a class="brand" href="../index.html"><img class="logo" src="../assets/img/logo.png" alt="">六级真题精读</a>
    <a class="tools" style="margin:0;text-decoration:none" href="../index.html">精读站</a>
    <button class="tools" style="margin:0" onclick="toggleTheme()">◐</button>
  </div>
</header>
<div class="wrap">

<div class="hero plan-hero">
  <h1>六级 62 天备考计划</h1>
  <p class="sub" id="examLine"></p>
  <div class="countdown" id="cd">—<small>天后考试</small></div>
  <div class="pbar"><i id="pbar" style="width:0"></i></div>
  <div class="pmeta" id="pmeta"></div>
</div>

<div class="card today" id="todayCard"></div>

<div class="card">
  <h2><span class="tag">进度</span>62 天一览</h2>
  <p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 4px">
    蓝=阶段一（阅读+听力）· 黄=阶段二（加写作翻译）· 红=阶段三（模考复盘）。点格子跳转。</p>
  <div class="wk" id="grid"></div>
</div>

<div class="card">
  <h2><span class="tag">清单</span>逐日任务</h2>
  <div class="daylist" id="daylist"></div>
</div>

<div class="card">
  <h2><span class="tag">说明</span>三个阶段</h2>
  <div class="phase-card p1"><b>阶段一 · 10/11–11/08（29 天）</b>
    <p style="font-size:13.5px;line-height:1.8;margin:6px 0 0">
      只做<strong>阅读 + 听力</strong>，写作翻译完全不碰。阅读一天一篇，走四步：
      按方法做题 → 核实对错（写清错因）→ 精读全文（生词查出来写在旁边）→ 在句子里背单词。<br>
      顺序：选词填空（最简单）→ 仔细阅读 → 长篇阅读（留到阶段二）。<br>
      听力每天模仿：听懂→模仿；听不懂→再听一遍；两遍还不懂→看原文查词，再听再模仿。模仿句数 5→10→15 递增。</p></div>
  <div class="phase-card p2"><b>阶段二 · 11/09–11/30（22 天）</b>
    <p style="font-size:13.5px;line-height:1.8;margin:6px 0 0">
      加<strong>写作 + 翻译</strong>（核心是语法，语法别错，不会写的词就降级表达）。
      阅读减为隔天一篇，转入复盘。听力继续模仿。</p></div>
  <div class="phase-card p3"><b>阶段三 · 12/01–12/11（11 天）</b>
    <p style="font-size:13.5px;line-height:1.8;margin:6px 0 0">
      <strong>整套模考</strong>（按考试时间一次做完）+ 复盘错题本和生词本。不再做新题。</p></div>
  <p style="font-size:13px;color:var(--fg-faint);margin-top:14px">
    勾选状态存在本机浏览器（<code>cet6:plan</code>）。「本篇收词 N」读的是精读站的生词本，
    跨页自动同步。换设备请用下方导出/导入。</p>
  <div class="tools" style="margin-top:8px">
    <button class="ghost" onclick="exportPlan()">导出进度</button>
    <button class="ghost" onclick="document.getElementById('impf').click()">导入进度</button>
    <input type="file" id="impf" accept=".json" hidden onchange="importPlan(this)">
    <button class="ghost" onclick="resetPlan()">清空进度</button>
  </div>
</div>

<footer class="site">
  <p>计划依据《建议.txt》（两个月备考讲座）编排，仅供个人学习使用。</p>
</footer>
</div>

<script>
var PLAN = __DATA__;
var LS_KEY = 'cet6:plan';
var VOCAB_KEY = 'cet6:vocab';
var MN = PLAN.module_names;

function $(id){ return document.getElementById(id); }
function esc(s){ var d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }
function todayStr(){
  var d=new Date();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function loadProg(){ try{ return JSON.parse(localStorage.getItem(LS_KEY))||{}; }catch(e){ return {}; } }
function saveProg(p){ try{ localStorage.setItem(LS_KEY, JSON.stringify(p)); }catch(e){} }
function loadVocab(){ try{ return JSON.parse(localStorage.getItem(VOCAB_KEY))||[]; }catch(e){ return []; } }

/* 一次性迁移：起始日从 2026-10-10 挪到 10-11 那次。
   每天的任务是按第几天（day_no）排的，和日历无关，所以日期整体后移一天、
   旧的打卡键同步 +1 天即可对得上。用版本标记保证只跑一次（幂等）。 */
function shiftDay(s, n){
  var d = new Date(s+'T00:00:00');
  d.setDate(d.getDate()+n);
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function migratePlan(){
  var VER_KEY = 'cet6:planVer';
  try{
    if(localStorage.getItem(VER_KEY) === PLAN.start_date) return;
    var OLD_LO = '2026-10-10', OLD_HI = '2026-12-17';   // 旧计划的起止日期（含）
    var p = loadProg(), q = {}, moved = 0;
    Object.keys(p).forEach(function(k){
      if(k >= OLD_LO && k <= OLD_HI){ q[shiftDay(k,1)] = p[k]; moved++; }
      else { q[k] = p[k]; }
    });
    if(moved) saveProg(q);
    localStorage.setItem(VER_KEY, PLAN.start_date);
  }catch(e){}
}

/* 统计某篇收了多少词：cet6:vocab[].src === "<set>/<mod>" */
function vocabCount(set, mod){
  if(!set||!mod) return 0;
  var key = set+'/'+mod;
  return loadVocab().filter(function(v){ return v && v.src === key; }).length;
}
/* 该套总共收了多少词 */
function vocabCountSet(set){
  if(!set) return 0;
  return loadVocab().filter(function(v){ return v && v.src && v.src.split('/')[0] === set; }).length;
}

function modLink(set, mod){
  if(!set) return null;
  return mod ? ('../p/'+set+'/'+mod+'.html') : ('../p/'+set+'.html');
}

function dayDone(dayObj, prog){
  var p = prog[dayObj.d];
  if(!p) return false;
  if(dayObj.steps && dayObj.steps.length){
    return dayObj.steps.every(function(s){ return p[s]; });
  }
  return !!p.__done;
}

function render(){
  var prog = loadProg();
  var td = todayStr();
  var exam = new Date(PLAN.exam_date+'T00:00:00');
  var now = new Date(td+'T00:00:00');
  var left = Math.round((exam-now)/86400000);

  $('examLine').textContent = '考试日期 '+PLAN.exam_date+'（周六） · 共 '+PLAN.days.length+' 天';
  $('cd').innerHTML = (left>0?left:0)+'<small>天后考试</small>';

  var doneN = PLAN.days.filter(function(d){ return dayDone(d,prog); }).length;
  $('pbar').style.width = Math.round(doneN/PLAN.days.length*100)+'%';
  $('pmeta').textContent = '已完成 '+doneN+' / '+PLAN.days.length+' 天 · 阅读计划 '+PLAN.stats.reading_planned+' 篇 · 听力 '+PLAN.stats.listen_sets+' 套循环';

  /* 今日卡片 */
  var t = PLAN.days.filter(function(x){ return x.d===td; })[0];
  if(!t){
    var next = PLAN.days.filter(function(x){ return x.d>td; })[0];
    $('todayCard').innerHTML = '<h2><span class="tag">今天</span>'+
      (next? '计划从 '+next.d+' 开始' : '计划已结束') +'</h2>'+
      '<p style="font-size:13.5px;color:var(--fg-soft)">'+
      (next? '点下方清单查看该日任务。' : '考试就在眼前，把错题本和生词本过一遍。')+'</p>';
  } else {
    $('todayCard').innerHTML = todayHTML(t, prog);
    bindSteps(t, prog);
    /* 今日卡片被整体重建了，重新填一下「今天的鼓励」（quotes.js 只填没填过的卡片） */
    if(window.CET6Quotes) window.CET6Quotes.fill();
  }

  /* 日历格子 */
  var g = PLAN.days.map(function(d){
    var cls = 'p'+d.phase;
    if(dayDone(d,prog)) cls += ' done';
    if(d.d===td) cls += ' today';
    if(d.d>td) cls += ' future';
    return '<div class="'+cls+'" title="'+d.d+' 第'+d.day+'天" onclick="jump(\''+d.d+'\')">'+
           '<span>'+d.day+'</span></div>';
  }).join('');
  $('grid').innerHTML = g;

  /* 逐日清单 */
  $('daylist').innerHTML = PLAN.days.map(function(d){
    return rowHTML(d, prog, td);
  }).join('');
  PLAN.days.forEach(function(d){ bindSteps(d, prog); });
}

function readingLine(r){
  if(!r) return '<span style="color:var(--fg-faint)">今日无新阅读</span>';
  var label = MN[r.mod] || '整套';
  var href = modLink(r.set, r.mod);
  var vt = vocabCount(r.set, r.mod);
  var vtag = vt ? ' <span class="vok">本篇收词 '+vt+'</span>' : '';
  if(r.whole){
    return '<span class="tagx">整套模考</span><a href="'+modLink(r.set,null)+'">'+r.set+'</a>'+
           ' <span class="vok">本套累计收词 '+vocabCountSet(r.set)+'</span>';
  }
  return '<span class="tagx">'+label+'</span><a href="'+href+'">'+r.set+' · '+label+'</a>'+vtag;
}

function listenLine(l){
  if(!l) return '';
  var href = modLink(l.set, l.mod);
  var n = l.sentences || l.imitate_sentences || 10;
  return '<span class="tagx">听力</span><a href="'+href+'">'+l.set+'</a> '+
         '<span style="color:var(--fg-soft)">模仿 '+n+' 句</span>';
}

function todayHTML(d, prog){
  var h = '<div class="th"><span class="tag">今天</span><b>第 '+d.day+' 天 · '+d.d+' '+d.weekday+'</b>'+
          '<span style="font-size:12.5px;color:var(--fg-faint)">阶段'+d.phase+'</span></div>';
  h += '<div class="big">'+readingLine(d.reading)+'</div>';
  if(d.listening) h += '<div style="margin-top:6px">'+listenLine(d.listening)+'</div>';
  if(d.extra){
    var lab = MN[d.extra.mod]||d.extra.mod;
    h += '<div style="margin-top:6px"><span class="tagx">'+lab+'</span>'+
         '<a href="'+modLink(d.extra.set,d.extra.mod)+'">'+d.extra.set+' · '+lab+'</a></div>';
  }
  if(d.note) h += '<div class="note">'+esc(d.note)+'</div>';
  h += stepsHTML(d, prog);
  /* 今天的鼓励：按第几天取一句温柔台词（quotes.js 填内容） */
  h += '<div class="qcard qsmall" data-quote="day" data-day="'+d.day+'"></div>';
  return h;
}

function stepsHTML(d, prog){
  if(!d.steps || !d.steps.length) return '';
  var p = prog[d.d] || {};
  var s = d.steps.map(function(st){
    return '<span class="dstep'+(p[st]?' on':'')+'" data-day="'+d.d+'" data-step="'+esc(st)+'">'+
           (p[st]?'✓ ':'')+esc(st)+'</span>';
  }).join('');
  return '<div class="dsteps">'+s+'</div>';
}

function rowHTML(d, prog, td){
  var done = dayDone(d,prog);
  var cls = 'dayrow'+(d.d===td?' today':'');
  var h = '<div class="'+cls+'"><div class="dh"><b>第 '+d.day+' 天 · '+d.d+' '+d.weekday+
          '</b><span class="dt">阶段'+d.phase+(done?' · <span class="vok">已完成</span>':'')+'</span></div>';
  h += '<div class="body">'+readingLine(d.reading);
  if(d.listening) h += '<br>'+listenLine(d.listening);
  if(d.extra){
    var lab = MN[d.extra.mod]||d.extra.mod;
    h += '<br><span class="tagx">'+lab+'</span><a href="'+modLink(d.extra.set,d.extra.mod)+'">'+
         d.extra.set+' · '+lab+'</a>';
  }
  h += '</div>';
  if(d.note) h += '<div class="note">'+esc(d.note)+'</div>';
  h += stepsHTML(d, prog);
  h += '</div>';
  return h;
}

/* 只刷新某一天的步骤按钮与相关 UI，避免重建整页 DOM */
function updateStepsUI(dayId, prog){
  var p = prog[dayId] || {};
  var list = document.querySelectorAll('.dstep[data-day="'+dayId+'"]');
  for(var i=0;i<list.length;i++){
    var el = list[i];
    var st = el.dataset.step;
    var on = !!p[st];
    if(on) el.classList.add('on'); else el.classList.remove('on');
    el.textContent = (on ? '✓ ' : '') + st;
  }
  var d = null;
  for(var k=0;k<PLAN.days.length;k++){
    if(PLAN.days[k].d === dayId){ d = PLAN.days[k]; break; }
  }
  if(!d) return;
  var done = dayDone(d, prog);
  var cells = document.querySelectorAll('#grid div');
  for(var m=0;m<cells.length;m++){
    if((cells[m].title||'').indexOf(dayId)===0){
      if(done) cells[m].classList.add('done'); else cells[m].classList.remove('done');
    }
  }
  var rows = document.querySelectorAll('.dayrow');
  for(var n=0;n<rows.length;n++){
    var b = rows[n].querySelector('.dh b');
    if(b && b.textContent.indexOf(dayId)>=0){
      var t = rows[n].querySelector('.dt');
      if(t) t.innerHTML = '阶段' + d.phase +
        (done ? ' · <span class="vok">已完成</span>' : '');
    }
  }
}

/* 只刷新顶部进度统计 */
function updateStats(prog){
  var doneN = 0;
  for(var i=0;i<PLAN.days.length;i++){
    if(dayDone(PLAN.days[i], prog)) doneN++;
  }
  var pb = document.getElementById('pbar');
  if(pb) pb.style.width = Math.round(doneN/PLAN.days.length*100)+'%';
  var pm = document.getElementById('pmeta');
  if(pm) pm.textContent = '已完成 ' + doneN + ' / ' + PLAN.days.length +
    ' 天 · 阅读计划 ' + PLAN.stats.reading_planned +
    ' 篇 · 听力 ' + PLAN.stats.listen_sets + ' 套循环';
}

function bindSteps(d, prog){
  document.querySelectorAll('.dstep[data-day="'+d.d+'"]').forEach(function(el){
    el.onclick = function(){
      var p = loadProg();
      if(!p[d.d]) p[d.d] = {};
      var st = el.dataset.step;
      p[d.d][st] = !p[d.d][st];
      if(d.steps.every(function(x){ return p[d.d][x]; })) p[d.d].__done = true;
      else delete p[d.d].__done;
      saveProg(p);
      updateStepsUI(d.d, p);
      updateStats(p);
    };
  });
}

function jump(date){
  var el = document.querySelector('.dayrow .dh b');
  var rows = document.querySelectorAll('.dayrow');
  for(var i=0;i<rows.length;i++){
    if(rows[i].querySelector('.dh b').textContent.indexOf(date)>=0){
      rows[i].scrollIntoView({behavior:'smooth', block:'center'});
      return;
    }
  }
}

function exportPlan(){
  var data = { plan: loadProg(), vocab: loadVocab() };
  var blob = new Blob([JSON.stringify(data,null,2)], {type:'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'cet6-备考进度-'+todayStr()+'.json';
  a.click();
}
function importPlan(inp){
  var f = inp.files && inp.files[0]; if(!f) return;
  var r = new FileReader();
  r.onload = function(){
    try{
      var d = JSON.parse(r.result);
      if(d.plan) saveProg(d.plan);
      render();
      alert('导入成功');
    }catch(e){ alert('文件格式不对'); }
  };
  r.readAsText(f);
}
function resetPlan(){
  if(!confirm('清空全部打卡进度？不可恢复。')) return;
  try{ localStorage.removeItem(LS_KEY); }catch(e){}
  render();
}

function toggleTheme(){
  var cur = document.documentElement.getAttribute('data-theme');
  var next = cur==='dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try{ localStorage.setItem('cet6-theme', next); }catch(e){}
}
(function(){
  try{
    var th = localStorage.getItem('cet6-theme');
    if(th) document.documentElement.setAttribute('data-theme', th);
  }catch(e){}
})();

migratePlan();
render();
</script>
<script src="../assets/quotes.js"></script>
</body>
</html>
"""