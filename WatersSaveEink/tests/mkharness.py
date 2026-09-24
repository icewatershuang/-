# -*- coding: utf-8 -*-
"""Build local render harnesses from a dashboard.html so we can LOOK at the layout.

Usage:  python _mkharness.py [source.html] [outprefix]
        default source = apk_extract/assets/dashboard.html , prefix = "orig"

  <prefix>.html  : untouched CSS  (modern Chromium, real flexbox)
  legacy.html    : unprefixed flexbox declarations stripped, so Chromium falls back
                   to -webkit-box / -webkit-flex (the 2009 spec) -- a decent
                   approximation of Android 4.0 WebKit 534.

The page is pinned to the real device canvas: 1200x825, topsir h9.
"""
import os, re, io, sys, hashlib

DEFAULT_SRC = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\assets\dashboard.html"
OUTDIR = r"D:\workbuddy\2026-09-23-08-21-00\_render"
os.makedirs(OUTDIR, exist_ok=True)

BRIDGE = (
    '<script>'
    'window.KindleBridge={'
    'getViewInfo:function(){return "1200|825|1200|825|1200|825|1|160|16";},'
    'getViewW:function(){return 1200;},getViewH:function(){return 825;},'
    'getDeviceModel:function(){return "topsir h9";}};'
    'window.KD_NATIVE_INFO="1200|825|1200|825|1200|825|1|160|16";'
    'try{window.fetch=function(){return new Promise(function(_,rj){rj(new Error("offline"));});};}catch(e){}'
    '</script>'
)
FORCE_H9 = (
    '<script>'
    'window.kdlIsH9=function(){return true;};'
    'try{ if((" "+document.documentElement.className+" ").indexOf(" kdl-h9 ")<0){'
    'document.documentElement.className=(document.documentElement.className+" kdl-h9").replace(/^\\s+/,"");}}catch(e){}'
    '</script>'
)
# Pin #stage to the exact device canvas (1200x825) at the top-left corner.
# Without this the headless window/viewport sizes disagree and the screenshot
# shows a different amount of the page than the DOM dump measured.
PIN_CANVAS = (
    '<style id="harnessPin">'
    'html,body{width:1200px !important;height:825px !important;overflow:hidden !important;}'
    '#stage{position:fixed !important;left:0 !important;top:0 !important;'
    'right:auto !important;bottom:auto !important;'
    'width:1200px !important;height:825px !important;}'
    '</style>'
)

SEED = r'''
<script>
/* ---- harness: seed news + weather, then force a full relayout ---- */
(function(){
  function run(){
    try{
      newsPool = [];
      var T = [
        "\u8fd9\u662f\u4e00\u6761\u7279\u522b\u957f\u7684\u65b0\u95fb\u6807\u9898\u7528\u6765\u6d4b\u8bd5\u81ea\u52a8\u6362\u884c\u662f\u5426\u751f\u6548\u5e94\u8be5\u4e00\u76f4\u6362\u884c\u6362\u5230\u5e95\u90e8\u800c\u4e0d\u662f\u88ab\u622a\u65ad\u6389",
        "\u77ed\u6807\u9898\u6d4b\u8bd5",
        "ANTIDISESTABLISHMENTARIANISM-LIKE-VERY-LONG-ENGLISH-TOKEN-TEST-1234567890",
        "\u4e2d\u56fd\u6559\u80b2\u90e8\u53d1\u5e03\u65b0\u5b66\u671f\u8bfe\u7a0b\u8ba1\u5212\uff0c\u5f3a\u8c03\u51cf\u8d1f\u4e0e\u7d20\u8d28\u6559\u80b2\u5e76\u91cd",
        "\u672c\u5730\u6c14\u8c61\u53f0\u53d1\u5e03\u9ad8\u6e29\u9ec4\u8272\u9884\u8b66\u4fe1\u53f7\u9884\u8ba1\u672a\u6765\u4e09\u5929\u6301\u7eed\u9ad8\u6e29"
      ];
      for (var i=0;i<T.length;i++){
        newsPool.push({date:"09-2"+(3-i), src:"\u6d4b\u8bd5\u6e90", title:T[i],
                       link:"#", ts:new Date().getTime(), pubRaw:""});
      }
      newsLoadDone = true;
      try{ CFG.newsPageSize = 5; }catch(e){}
      try{ applyVisibility(); }catch(e){}
      renderNewsPage();
      try{ renderNews(); }catch(e){}
      try{ reflowVertical(); }catch(e){}
      try{ applyFit({force:true}); }catch(e){}
      try{ kdV39Layout(); }catch(e){}
      try{ __diag(); }catch(e){}
      document.title = "READY " + document.documentElement.className;
      window.__kdReady = 1;
    }catch(err){
      document.title = "ERR " + err;
      window.__kdReady = -1;
    }
  }
  /* ---- geometry dump: written into #__diag so --dump-dom reveals real numbers ---- */
  function __diag(){
    function R(sel){
      var e = sel && sel.nodeType ? sel : document.querySelector(sel);
      if(!e){ return sel + "=MISSING"; }
      var r = e.getBoundingClientRect();
      var cs = window.getComputedStyle(e);
      return sel + " L" + Math.round(r.left) + " T" + Math.round(r.top) +
             " W" + Math.round(r.width) + " H" + Math.round(r.height) +
             " B" + Math.round(r.bottom) +
             " | disp=" + cs.display + " ws=" + cs.whiteSpace +
             " w=" + cs.width +
             " ov=" + cs.overflow + " pos=" + cs.position +
             " sw=" + e.scrollWidth + " cw=" + e.clientWidth;
    }
    var L = [];
    L.push("html=" + document.documentElement.className);
    L.push("viewport=" + window.innerWidth + "x" + window.innerHeight);
    ["#stage","#mainPage","#topWrap",".layout",".col-left",".col-right",".cl-inner",
     "#btnBar",".card-poem",".mid-row",".cr-wrap",".cr-body",
     ".news-scroll","#newsList"].forEach(function(s){ L.push(R(s)); });
    var ni = document.getElementsByClassName("news-item");
    L.push("newsItems=" + ni.length);
    for (var v = 0; v < ni.length; v++) {
      var tv = ni[v].getElementsByClassName("news-title")[0];
      var rh = tv ? Math.round(tv.getBoundingClientRect().height) : -1;
      var rw = tv ? Math.round(tv.getBoundingClientRect().width) : -1;
      var ovf = tv ? (tv.scrollWidth > tv.clientWidth + 1) : false;
      L.push("  item" + v + " titleW=" + rw + " titleH=" + rh +
             " overflowX=" + ovf + " sw=" + (tv?tv.scrollWidth:-1) +
             " cw=" + (tv?tv.clientWidth:-1));
    }
    L.push("---- inline styles under #topWrap ----");
    var all = document.getElementById("topWrap").getElementsByTagName("*");
    for (var q = 0; q < all.length; q++) {
      var sa = all[q].getAttribute("style");
      if (sa) {
        var idc = all[q].id ? ("#" + all[q].id) : "";
        L.push(all[q].tagName + idc + "." + (all[q].className || "") + "  ->  " + sa);
      }
    }
    /* runtime-injected stylesheets only (skip the three static <style> blocks) */
    L.push("---- runtime stylesheets ----");
    var STATIC = {baseCss:1, kdlEinkFix:1, kdlFix39:1};
    for (var s = 0; s < document.styleSheets.length; s++) {
      var ss = document.styleSheets[s];
      var on = ss.ownerNode;
      var oid = on ? (on.id || on.tagName) : "?";
      if (STATIC[oid]) { L.push("sheet[" + s + "] STATIC " + oid); continue; }
      var rules = null;
      try { rules = ss.cssRules || ss.rules; } catch (eR0) { rules = null; }
      var txt = "";
      if (rules) {
        try {
          for (var rr = 0; rr < rules.length; rr++) { txt += rules[rr].cssText + "\n"; }
        } catch (eR1) { txt = "<err " + eR1 + ">"; }
      }
      L.push("sheet[" + s + "] id=" + oid + " rules=" + (rules ? rules.length : -1));
      L.push(txt.length > 6000 ? txt.slice(0, 6000) : txt);
    }
    var d = document.createElement("pre");
    d.id = "__diag";
    d.style.cssText = "position:fixed;left:-99999px;top:0;";
    var MK = "@@" + "BEG" + "MARK" + "@@";
    var EN = "@@" + "END" + "MARK" + "@@";
    d.textContent = "\n" + MK + "\n" + L.join("\n") + "\n" + EN + "\n";
    document.body.appendChild(d);
  }
  function later(){ setTimeout(run, 3000); setTimeout(run, 8000); }
  if (document.readyState === "complete") { later(); }
  else { window.addEventListener("load", later, false); }
})();
</script>
</body>
'''

FLEX_PROPS = (
    "flex", "flex-direction", "flex-wrap", "flex-flow", "flex-grow",
    "flex-shrink", "flex-basis", "justify-content", "align-items", "align-self",
    "align-content", "order",
)


def strip_unprefixed_flex(css):
    """Remove un-prefixed flexbox declarations; keep -webkit-* ones.

    `display` is only dropped when its value is flex / inline-flex --
    a blanket drop would also kill `display:none` / `display:block`.
    """
    out = []
    i = 0
    n = len(css)
    while i < n:
        j = css.find(";", i)
        if j < 0:
            out.append(css[i:]); break
        decl = css[i:j]
        seg = css[i:j+1]
        m = re.match(r"\s*([-a-zA-Z]+)\s*:(.*)$", decl, re.S)
        if m:
            prop = m.group(1).lower()
            val = m.group(2).strip().lower()
            if prop in FLEX_PROPS or (prop == "display" and "flex" in val):
                seg = ""
        out.append(seg)
        i = j + 1
    return "".join(out)


def strip_style_blocks(html):
    return re.sub(r"<style([^>]*)>(.*?)</style>",
                  lambda m: "<style" + m.group(1) + ">" +
                            strip_unprefixed_flex(m.group(2)) + "</style>",
                  html, flags=re.S | re.I)


def build(src, prefix):
    html = io.open(src, "r", encoding="utf-8", errors="replace").read()
    idx = html.find("<style")
    html = html[:idx] + BRIDGE + "\n" + FORCE_H9 + "\n" + html[idx:]
    hd = html.rfind("</head>")
    if hd > 0:
        html = html[:hd] + PIN_CANVAS + html[hd:]
    k = html.rfind("</body>")
    html = html[:k] + SEED + html[k + len("</body>"):]

    modern = os.path.join(OUTDIR, prefix + ".html")
    legacy = os.path.join(OUTDIR, prefix + "_legacy.html")
    io.open(modern, "w", encoding="utf-8").write(html)
    io.open(legacy, "w", encoding="utf-8").write(strip_style_blocks(html))
    print("%-22s %s" % (prefix + ".html", os.path.getsize(modern)))
    print("%-22s %s" % (prefix + "_legacy.html", os.path.getsize(legacy)))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    pref = sys.argv[2] if len(sys.argv) > 2 else "orig"
    build(src, pref)
