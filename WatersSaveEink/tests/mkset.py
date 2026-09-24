# -*- coding: utf-8 -*-
"""生成「设置页滚动」实测页：打开设置 → 合成触摸拖拽 → 量几何。

输出 _render/set.html 与 _render/set_legacy.html（后者剥离无前缀 flexbox，近似安卓4.0 的 WebKit 534）。
"""
import io, os, re, sys

sys.path.insert(0, r"D:\workbuddy\2026-09-23-08-21-00")
import _mkharness as H   # noqa: E402

OUTDIR = H.OUTDIR

# 设备是水墨屏 + H9（详见 dashboard.html 自身注释：Top sir h9 / 安卓 4.0）
FORCE_EINK = (
    '<script>'
    'window.kdlIsH9=function(){return true;};'
    'try{var e=document.documentElement,c=(" "+e.className+" ");'
    'if(c.indexOf(" kdl-h9 ")<0){e.className=(e.className+" kdl-h9").replace(/^\\s+/,"");}'
    'c=(" "+e.className+" ");'
    'if(c.indexOf(" kd-eink ")<0){e.className=(e.className+" kd-eink").replace(/^\\s+/,"");}}catch(err){}'
    '</script>'
)

SEED2 = r'''
<script>
(function(){
  function longList(n, cls, inner){
    var s = "";
    for (var i = 0; i < n; i++) { s += '<div class="' + cls + '"><span class="nm">' + inner + " " + i + '</span></div>'; }
    return s;
  }
  function T(y, type, target){
    target = target || document.getElementById("settingsMask");
    var t = new Touch({identifier: 1, target: target, clientX: 600, clientY: y,
                       pageX: 600, pageY: y, screenX: 600, screenY: y});
    var empty = (type === "touchend" || type === "touchcancel");
    var ev = new TouchEvent(type, {
      touches: empty ? [] : [t],
      targetTouches: empty ? [] : [t],
      changedTouches: [t],
      bubbles: true, cancelable: true
    });
    target.dispatchEvent(ev);
  }
  function geo(sel){
    var e = (typeof sel === "string") ? document.querySelector(sel) : sel;
    if (!e) { return String(sel) + "=MISSING"; }
    var r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return String(sel) + " L" + Math.round(r.left) + " T" + Math.round(r.top) +
           " W" + Math.round(r.width) + " H" + Math.round(r.height) +
           " B" + Math.round(r.bottom) +
           " | ov=" + cs.overflow + " ovY=" + cs.overflowY + " tf=" + cs.transform +
           " pos=" + cs.position + " ch=" + e.clientHeight + " oh=" + e.offsetHeight;
  }
  function run(){
    var L = [];
    try {
      /* 1) 先打开设置页，等它的所有延迟渲染跑完（渲染器会覆盖我们灌的内容） */
      openSettings();
      setTimeout(stage2, 1800);
    } catch (e) {
      document.title = "SET ERR " + e;
    }
  }
  function stage2(){
    var L = [];
    try {
      /* 2) 展开所有折叠分类，否则里面的盒子是 0x0，量不到 */
      var cats = document.querySelectorAll("#settingsMask .cat");
      for (var ci = 0; ci < cats.length; ci++) { cats[ci].className = "cat"; }
      try { resetCats && 0; } catch (eC) {}

      /* 3) 灌长内容，保证三处清单都"该能滚"
         （设置页里的搜索结果盒是 #radioResults，#radioResults2 在弹窗里；播放清单是 #radioMyListS） */
      var rr = document.getElementById("radioResults");
      if (rr) { rr.innerHTML = longList(40, "radio-my-row", "\u6d4b\u8bd5\u7535\u53f0"); }
      var rm = document.getElementById("radioMyListS");
      if (rm) { rm.innerHTML = '<div class="radio-my-title">\u6211\u7684\u7535\u53f0</div>' +
                               longList(30, "radio-my-row", "\u6211\u7684\u7535\u53f0"); }
      var fl = document.querySelectorAll("#secMusic .j-mu-files");
      for (var f = 0; f < fl.length; f++) { fl[f].innerHTML = longList(40, "mu-item", "\u66f2\u76ee"); }
      var rss = document.getElementById("rssList");
      if (rss) { rss.innerHTML = longList(50, "rss-row", "\u65b0\u95fb\u6e90"); }

      setTimeout(stage3, 400);
    } catch (e2) {
      document.title = "SET ERR2 " + e2;
    }
  }
  function stage3(){
    var L = [];
    /* 拖拽前即时灌满（有些清单会被自己的定时重渲染覆盖，间隔太久会量不到） */
    function innerTest(sel, rows, cls){
      var box = document.querySelector(sel);
      if (!box) { L.push("INNER " + sel + " = MISSING"); return; }
      box.innerHTML = longList(rows, cls, "\u9879\u76ee");
      var chk = box.children.length;
      var h1 = box.firstElementChild;
      var t1 = h1 ? getComputedStyle(h1).transform : "?";
      var can1 = _kdlShiftCan(box);
      T(500, "touchstart", h1 || box);
      T(460, "touchmove", h1 || box);
      T(420, "touchmove", h1 || box);
      T(380, "touchmove", h1 || box);
      T(380, "touchend", h1 || box);
      var h2 = box.firstElementChild;
      var t2 = h2 ? getComputedStyle(h2).transform : "?";
      L.push("INNER " + sel + ": filled=" + chk + " canScroll=" + can1 +
             " before=" + t1 + " after=" + t2 +
             " off=" + Math.round(_kdlShiftGet(box)) +
             " maxShift=" + Math.round(_kdlShiftMax(box, _kdlShiftHost(box))) +
             " children=" + box.children.length +
             " childClass=" + (h2 ? h2.className : "?") +
             " ch=" + box.clientHeight);
    }
    try {
          L.push("== SETTINGS SCROLL TEST ==");
          L.push("html=" + document.documentElement.className);
          L.push("viewport=" + window.innerWidth + "x" + window.innerHeight);
          L.push("settingsMaxScroll=" + settingsMaxScroll());
          L.push("maskStyle=" + (document.getElementById("settingsMask").getAttribute("style") || ""));
          L.push(geo("#settingsMask"));
          L.push(geo("#settingsMask .modal"));
          L.push(geo("#rssList"));
          L.push(geo("#radioResults"));
          L.push(geo("#radioMyListS"));
          L.push(geo("#secMusic .j-mu-files"));

          /* ---- A. 外层设置页：合成触摸拖拽（手指上滑 300px） ---- */
          var mask = document.getElementById("settingsMask");
          var modal = mask.firstElementChild;
          var before = getComputedStyle(modal).transform;
          var maxS = settingsMaxScroll();
          T(600, "touchstart", mask);
          T(500, "touchmove", mask);
          T(400, "touchmove", mask);
          T(300, "touchmove", mask);
          T(300, "touchend", mask);
          var after = getComputedStyle(modal).transform;
          L.push("OUTER drag: before=" + before + " after=" + after +
                 " _sTop=" + Math.round(_sTop) + " max=" + Math.round(maxS));

          /* ---- B/C. 四处次级清单各自拖一次 ---- */
          innerTest("#radioResults", 40, "radio-my-row");
          innerTest("#radioMyListS", 30, "radio-my-row");
          innerTest("#secMusic .j-mu-files", 40, "mu-item");
          innerTest("#rssList", 50, "rss-row");
          L.push("OUTER _sTop after inner drags=" + Math.round(_sTop) + " (内层能滚时外层不该动)");

          /* ---- D. 滚到底再继续上滑 -> 应"接力"给外层 ---- */
          setSettingsScroll(0);
          var box = document.getElementById("radioResults");
          if (box) {
            var host = box.firstElementChild;
            _kdlShiftSet(box, 1e6);              /* 先顶到内层底部 */
            var baseTop = _sTop;
            T(400, "touchstart", host || box);
            T(340, "touchmove", host || box);    /* 继续上滑：内层已到底 -> 接力 */
            T(280, "touchmove", host || box);
            T(280, "touchend", host || box);
            L.push("RELAY: _sTop " + Math.round(baseTop) + " -> " + Math.round(_sTop) +
                   " boxOff=" + Math.round(_kdlShiftGet(box)) + " (外层应开始动)");
          }

          /* ---- E. 回归对照：把被删掉的旧规则加回去，外层应立刻推不动 ---- */
          setSettingsScroll(0);
          var st = document.createElement("style");
          st.textContent = "html.kd-eink #settingsMask > * { -webkit-transform: none !important; transform: none !important; }";
          document.head.appendChild(st);
          var md = mask.firstElementChild;
          T(600, "touchstart", mask);
          T(400, "touchmove", mask);
          T(200, "touchmove", mask);
          T(200, "touchend", mask);
          L.push("WITH OLD RULE: _sTop=" + Math.round(_sTop) +
                 " modalTransform=" + getComputedStyle(md).transform +
                 "  <-- 状态在变但画面不动 = 用户看到的'拉不动'");
    } catch (eD) {
      L.push("DIAG ERR " + eD);
    }
    var d = document.createElement("pre");
    d.id = "__setdiag";
    d.style.cssText = "position:fixed;left:-99999px;top:0;";
    var MK = "@@" + "SET" + "BEG" + "@@", EN = "@@" + "SET" + "END" + "@@";
    d.textContent = "\n" + MK + "\n" + L.join("\n") + "\n" + EN + "\n";
    document.body.appendChild(d);
    document.title = "SETTINGS READY";
  }
  if (document.readyState === "complete") { setTimeout(run, 2500); }
  else { window.addEventListener("load", function(){ setTimeout(run, 2500); }, false); }
})();
</script>
</body>
'''


def build(src, prefix, legacy=False):
    html = io.open(src, "r", encoding="utf-8", errors="replace").read()
    idx = html.find("<style")
    html = html[:idx] + H.BRIDGE + "\n" + FORCE_EINK + "\n" + html[idx:]
    hd = html.rfind("</head>")
    if hd > 0:
        html = html[:hd] + H.PIN_CANVAS + html[hd:]
    k = html.rfind("</body>")
    html = html[:k] + SEED2 + html[k + len("</body>"):]
    if legacy:
        html = H.strip_style_blocks(html)
    out = os.path.join(OUTDIR, prefix + ".html")
    io.open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, os.path.getsize(out))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else H.DEFAULT_SRC
    build(src, "set", legacy=False)
    build(src, "set_legacy", legacy=True)
