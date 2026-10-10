/* ==========================================================================
   答题交互（就地改造 DOM 版）

   不需要 gen_site.py 做任何特殊渲染，本模块自己从现有页面结构里
   提取题目、选项、答案，然后改造成可点的选择题。

   适配的现有结构：
     仔细阅读/听力  <div class="q"> <span class="q-no">46</span> ...
                    <ul class="opts"><li class="correct"><span class="ltr">D)</span>...
                    <div class="ansbadge">D<span class="qt">（细节题）</span></div>
     长篇阅读       <div class="q"> <span class="q-no">36</span> ...
                    <div class="ansbadge">答案：I 段</div>
     选词填空       <div class="q" data-qno="26" data-answer="N">
                    <div class="ansbadge" hidden>N) surpass动词</div>
                    正文里的空位：<span class="cslot" data-qno="26">
                    词库：<li class="wb-item" data-letter="N" data-word="surpass">

   存储（与 word.js 兼容）：
     cet6:answers  作答 { "<set>/<mod>/<no>": {my, ok, t} }
     cet6:wrong    错题 [{set, mod, no, my, ans, t}]
   ========================================================================== */
(function () {
  "use strict";

  var ANS_KEY = "cet6:answers";
  var WRONG_KEY = "cet6:wrong";

  function load(k, d) {
    try { var s = localStorage.getItem(k); return s ? JSON.parse(s) : d; } catch (e) { return d; }
  }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  var answers = load(ANS_KEY, {});
  var wrong = load(WRONG_KEY, []);
  if (!Array.isArray(wrong)) wrong = [];
  if (!answers || typeof answers !== "object" || Array.isArray(answers)) answers = {};

  function pageId() {
    var m = location.pathname.match(/\/p\/([^/]+)\/([^/.]+)\.html/);
    return m ? m[1] + "/" + m[2] : "";
  }
  function setId() { var p = pageId(); return p ? p.split("/")[0] : ""; }
  function modId() { var p = pageId(); return p ? p.split("/")[1] : ""; }
  function qkey(no) { return pageId() + "/" + no; }
  function norm(s) { return String(s == null ? "" : s).trim().toUpperCase().replace(/[^A-Z]/g, ""); }

  /* ---------- 从 DOM 抽题目信息 ---------- */

  function qnoOf(q) {
    if (q.dataset.qno) return q.dataset.qno;
    var el = q.querySelector(".q-no");
    return el ? el.textContent.replace(/[^0-9]/g, "") : "";
  }

  /* 仔细阅读/听力：从 .opts li 拿选项，从 .ansbadge 拿答案字母 */
  function readChoice(q) {
    var list = q.querySelector("ul.opts");
    if (!list) return null;
    var opts = [];
    list.querySelectorAll("li").forEach(function (li) {
      var ltrEl = li.querySelector(".ltr");
      var L = ltrEl ? norm(ltrEl.textContent) : norm(li.textContent).charAt(0);
      if (L) opts.push({ letter: L, li: li });
    });
    if (!opts.length) return null;
    var badge = q.querySelector(".ansbadge");
    var ans = "";
    if (badge) {
      ans = norm(badge.textContent).charAt(0);
    }
    if (!ans) {
      var c = list.querySelector("li.correct");
      if (c) { var le = c.querySelector(".ltr"); ans = le ? norm(le.textContent) : ""; }
    }
    return ans ? { opts: opts, answer: ans } : null;
  }

  /* 长篇阅读：从 .ansbadge 拿 "答案：I 段"，选项是 A..M */
  function readMatch(q) {
    var badge = q.querySelector(".ansbadge");
    if (!badge) return null;
    var t = badge.textContent || "";
    if (t.indexOf("段") < 0) return null;
    var m = t.match(/[A-Z]/);
    if (!m) return null;
    var letters = [];
    for (var i = 0; i < 13; i++) letters.push(String.fromCharCode(65 + i));
    return { answer: m[0], letters: letters };
  }

  /* 选词填空：题目容器自带 data-answer（gen_site 已写）*/
  function readCloze(q) {
    if (q.dataset.qtype === "cloze" && q.dataset.answer) {
      return { answer: norm(q.dataset.answer) };
    }
    var badge = q.querySelector(".ansbadge");
    if (!badge) return null;
    var t = (badge.textContent || "").trim();
    var m = t.match(/^([A-O])\)/);
    if (!m) return null;
    return { answer: m[1] };
  }

  /* ---------- 错题本 ---------- */
  function markWrong(no, my, ans) {
    wrong = wrong.filter(function (w) {
      return !(w && w.set === setId() && w.mod === modId() && String(w.no) === String(no));
    });
    wrong.unshift({ set: setId(), mod: modId(), no: no, my: my, ans: ans, t: Date.now() });
    save(WRONG_KEY, wrong);
  }
  function clearWrong(no) {
    var before = wrong.length;
    wrong = wrong.filter(function (w) {
      return !(w && w.set === setId() && w.mod === modId() && String(w.no) === String(no));
    });
    if (wrong.length !== before) save(WRONG_KEY, wrong);
  }

  /* ---------- 改造：仔细阅读/听力 ---------- */
  function buildChoice(q, info) {
    var no = qnoOf(q);
    var list = q.querySelector("ul.opts");
    list.classList.add("quiz-opts");
    list.querySelectorAll("li").forEach(function (li) {
      li.classList.remove("correct");
      li.classList.add("quiz-option");
      var le = li.querySelector(".ltr");
      li.dataset.letter = le ? norm(le.textContent) : "";
      li.addEventListener("click", function () {
        if (q.dataset.done) return;
        list.querySelectorAll("li").forEach(function (x) { x.classList.remove("sel"); });
        li.classList.add("sel");
        updateBar();
      });
    });
    q.dataset.answer = info.answer;
    q.dataset.qtype = "choice";
    q.dataset.qno = no;
    var b = q.querySelector(".ansbadge");
    if (b) b.hidden = true;
  }

  /* ---------- 改造：长篇阅读（下拉选段，带首句摘要） ---------- */
  function buildMatch(q, info) {
    var no = qnoOf(q);
    var sel = document.createElement("select");
    sel.className = "match-sel";
    sel.innerHTML = "<option value=\"\">选段落…</option>" +
      info.letters.map(function (L) {
        var hint = paraHint(L);
        return "<option value=\"" + L + "\">" + L + " 段" +
          (hint ? "：" + hint : "") + "</option>";
      }).join("");
    var head = q.querySelector(".q-head");
    if (head) head.appendChild(sel);
    else q.appendChild(sel);
    sel.addEventListener("change", updateBar);
    q.dataset.answer = info.answer;
    q.dataset.qtype = "match";
    q.dataset.qno = no;
    var b = q.querySelector(".ansbadge");
    if (b) b.hidden = true;
  }

  /* 从正文段落里取「A 段」首句前若干字，作为下拉提示 */
  var _paraHint = null;
  function paraHint(L) {
    if (!_paraHint) {
      _paraHint = {};
      document.querySelectorAll(".para").forEach(function (p) {
        var pno = p.querySelector(".pno");
        var en = p.querySelector(".en");
        if (!pno || !en) return;
        var key = pno.textContent.trim().replace(/[^A-Za-z]/g, "").toUpperCase();
        if (!key) return;
        var txt = en.textContent.trim().replace(/^[A-Z]\)\s*/, "");
        _paraHint[key] = txt.slice(0, 22) + (txt.length > 22 ? "…" : "");
      });
    }
    return _paraHint[L] || "";
  }

  /* ---------- 改造：选词填空（点词 -> 点空） ---------- */
  var clozeBank = [];      /* [{letter, word, el}] */
  var clozeSel = null;     /* 当前选中的词 */

  function buildClozeAll() {
    var slots = document.querySelectorAll(".cslot");
    var bankEls = document.querySelectorAll(".wb-item");
    if (!slots.length || !bankEls.length) return false;

    clozeBank = [];
    Array.prototype.forEach.call(bankEls, function (el) {
      clozeBank.push({
        letter: norm(el.dataset.letter),
        word: el.dataset.word || "",
        el: el
      });
      el.addEventListener("click", function () { pickWord(el); });
      el.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pickWord(el); }
      });
    });

    Array.prototype.forEach.call(slots, function (slot) {
      slot.addEventListener("click", function () { onSlot(slot); });
      slot.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onSlot(slot); }
      });
    });
    return true;
  }

  function pickWord(el) {
    if (el.classList.contains("used")) {
      /* 点已用的词 = 从空里退回来 */
      var no = el.dataset.onQno;
      if (no) {
        var slot = document.querySelector('.cslot[data-qno="' + no + '"]');
        if (slot) clearSlot(slot);
      }
      return;
    }
    if (clozeSel) clozeSel.classList.remove("picked");
    clozeSel = (clozeSel === el) ? null : el;
    if (clozeSel) clozeSel.classList.add("picked");
  }

  function onSlot(slot) {
    if (slot.classList.contains("locked")) return;
    /* 点已填的空 = 清空 */
    if (slot.dataset.letter) { clearSlot(slot); return; }
    if (!clozeSel) { flash(slot); return; }
    var L = norm(clozeSel.dataset.letter);
    var W = clozeSel.dataset.word || "";
    slot.dataset.letter = L;
    slot.dataset.word = W;
    var val = slot.querySelector(".cval");
    if (val) val.textContent = W;
    slot.classList.add("filled");
    clozeSel.classList.remove("picked");
    clozeSel.classList.add("used");
    clozeSel.dataset.onQno = slot.dataset.qno;
    clozeSel = null;
    updateBar();
  }

  function clearSlot(slot) {
    var L = slot.dataset.letter;
    slot.dataset.letter = "";
    slot.dataset.word = "";
    var val = slot.querySelector(".cval");
    if (val) val.textContent = "";
    slot.classList.remove("filled", "q-ok", "q-bad");
    if (L) {
      var wEl = document.querySelector('.wb-item[data-letter="' + L + '"]');
      if (wEl) {
        wEl.classList.remove("used");
        delete wEl.dataset.onQno;
      }
    }
    updateBar();
  }

  function flash(el) {
    el.classList.add("flash");
    setTimeout(function () { el.classList.remove("flash"); }, 500);
  }

  function clozePick(q) {
    var no = q.dataset.qno;
    var slot = document.querySelector('.cslot[data-qno="' + no + '"]');
    return slot ? norm(slot.dataset.letter) : "";
  }

  /* ---------- 判分 ---------- */
  function pickOf(q) {
    var t = q.dataset.qtype;
    if (t === "choice") {
      var on = q.querySelector("ul.opts li.sel");
      return on ? norm(on.dataset.letter) : "";
    }
    if (t === "cloze") return clozePick(q);
    var sel = q.querySelector("select");
    return sel ? norm(sel.value) : "";
  }

  function judge(q, my) {
    var no = q.dataset.qno || "";
    var ans = norm(q.dataset.answer);
    var ok = (my === ans);
    answers[qkey(no)] = { my: my, ok: ok, t: Date.now() };
    save(ANS_KEY, answers);
    if (ok) clearWrong(no); else markWrong(no, my, ans);

    q.dataset.done = "1";
    q.classList.add(ok ? "q-ok" : "q-bad");

    if (q.dataset.qtype === "choice") {
      q.querySelectorAll("ul.opts li").forEach(function (li) {
        var L = norm(li.dataset.letter);
        li.classList.remove("sel");
        if (L === ans) li.classList.add("correct");
        else if (L === my && !ok) li.classList.add("chosen-bad");
      });
      var b = q.querySelector(".ansbadge");
      if (b) b.hidden = false;
    } else if (q.dataset.qtype === "cloze") {
      var slot = document.querySelector('.cslot[data-qno="' + no + '"]');
      if (slot) {
        slot.classList.add("locked", ok ? "q-ok" : "q-bad");
        var tip = document.createElement("i");
        tip.className = "cslot-tip";
        tip.textContent = ok ? "✓" : "✗ " + ans;
        slot.appendChild(tip);
      }
      var bb = q.querySelector(".ansbadge");
      if (bb && !ok) bb.hidden = false;
    } else {
      var sel = q.querySelector("select");
      if (sel) sel.disabled = true;
      var b2 = q.querySelector(".ansbadge");
      if (b2) b2.hidden = false;
    }

    if (q.dataset.qtype !== "cloze") {
      var box = q.querySelector(".quiz-res");
      if (!box) { box = document.createElement("div"); box.className = "quiz-res"; q.appendChild(box); }
      box.innerHTML = ok
        ? "<span class=\"qr-ok\">✓ 答对了</span>"
        : "<span class=\"qr-bad\">✗ 你选了 " + (my || "空") + "，正确答案 " + ans + "</span>";
    }
  }

  function restore(q) {
    var no = q.dataset.qno || "";
    var rec = answers[qkey(no)];
    if (!rec) return;
    if (q.dataset.qtype === "choice") {
      q.querySelectorAll("ul.opts li").forEach(function (li) {
        if (norm(li.dataset.letter) === norm(rec.my)) li.classList.add("sel");
      });
    } else if (q.dataset.qtype === "cloze") {
      var slot = document.querySelector('.cslot[data-qno="' + no + '"]');
      if (slot && rec.my) {
        var L = norm(rec.my);
        var wEl = document.querySelector('.wb-item[data-letter="' + L + '"]');
        if (wEl) {
          slot.dataset.letter = L;
          slot.dataset.word = wEl.dataset.word || "";
          var val = slot.querySelector(".cval");
          if (val) val.textContent = wEl.dataset.word || "";
          slot.classList.add("filled");
          wEl.classList.add("used");
          wEl.dataset.onQno = no;
        }
      }
    } else {
      var sel = q.querySelector("select");
      if (sel && rec.my) sel.value = rec.my;
    }
    judge(q, norm(rec.my));
  }

  function submitOne(q) {
    if (q.dataset.done) return null;
    var my = pickOf(q);
    if (!my) return "empty";
    var ans = norm(q.dataset.answer);
    judge(q, my);
    return my === ans ? "ok" : "bad";
  }

  /* ---------- 底部提交栏 ---------- */
  var bar = null, items = [];
  function buildBar() {
    bar = document.createElement("div");
    bar.className = "quiz-bar";
    bar.innerHTML = "<span class=\"qb-stat\" id=\"qbStat\"></span>" +
      "<button type=\"button\" class=\"qb-btn\" id=\"qbSubmit\">提交答案</button>" +
      "<button type=\"button\" class=\"qb-btn qb-ghost\" id=\"qbClear\">重做本篇</button>";
    document.body.appendChild(bar);
    bar.querySelector("#qbSubmit").onclick = submitAll;
    bar.querySelector("#qbClear").onclick = resetAll;
  }

  function updateBar() {
    if (!bar) return;
    var picked = 0, judged = 0, right = 0;
    items.forEach(function (q) {
      if (pickOf(q)) picked++;
      if (q.classList.contains("q-ok")) { judged++; right++; }
      else if (q.classList.contains("q-bad")) judged++;
    });
    var st = bar.querySelector("#qbStat");
    if (st) st.textContent = "共 " + items.length + " 题 · 已选 " + picked +
      (judged ? " · 已判 " + judged + "（对 " + right + "）" : "");
    var btn = bar.querySelector("#qbSubmit");
    if (btn) btn.disabled = (picked === 0);
  }

  function submitAll() {
    var ok = 0, bad = 0, empty = 0;
    items.forEach(function (q) {
      var r = submitOne(q);
      if (r === "ok") ok++; else if (r === "bad") bad++; else if (r === "empty") empty++;
    });
    updateBar();
    var m = [];
    if (ok) m.push("对 " + ok + " 题");
    if (bad) m.push("错 " + bad + " 题（已记入错题本）");
    if (empty) m.push(empty + " 题未作答");
    alert(m.length ? m.join("，") : "没有可提交的题");
  }

  function resetAll() {
    if (!confirm("清空本篇的作答记录？（错题本不受影响）")) return;
    var pid = pageId();
    Object.keys(answers).forEach(function (k) {
      if (k.indexOf(pid + "/") === 0) delete answers[k];
    });
    save(ANS_KEY, answers);
    location.reload();
  }

  /* ---------- 启动 ---------- */
  function init() {
    var clozeMode = buildClozeAll();

    var qs = document.querySelectorAll(".q");
    Array.prototype.forEach.call(qs, function (q) {
      var t = readChoice(q);
      if (t) { buildChoice(q, t); }
      else {
        var m = readMatch(q);
        if (m) { buildMatch(q, m); }
        else {
          var c = readCloze(q);
          if (c) { q.dataset.qtype = "cloze"; if (!q.dataset.qno) q.dataset.qno = qnoOf(q); }
        }
      }
      // 错题本要能跳到具体题目：p/<set>/<mod>.html#q46
      if (q.dataset.qno) q.id = "q" + q.dataset.qno;
    });

    // 从错题本点过来：滚到那道题并闪一下（不自动显示答案，留着重做）
    if (/^#q\d+$/.test(location.hash || "")) {
      var target = document.getElementById(location.hash.slice(1));
      if (target) {
        target.scrollIntoView({ block: "center" });
        target.classList.add("q-flash");
        setTimeout(function () { target.classList.remove("q-flash"); }, 1600);
      }
    }

    items = Array.prototype.filter.call(document.querySelectorAll(".q"), function (q) {
      return !!q.dataset.answer;
    });
    if (!items.length && !clozeMode) return;

    buildBar();
    items.forEach(restore);
    updateBar();
    if (items.some(function (q) { return q.dataset.done; })) {
      document.body.classList.remove("hide-ans");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.CET6Quiz = { load: load, save: save };
})();
