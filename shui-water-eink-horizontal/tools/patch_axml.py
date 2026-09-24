# -*- coding: utf-8 -*-
import io, sys

SRC = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\assets\dashboard.html"
BAK = SRC + ".bak"

with io.open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# Work on a copy for safety
orig = html

def do(old, new, n=1):
    global html
    c = html.count(old)
    if c != n:
        raise SystemExit("EXPECTED %d occurrence(s) of:\n%r\nbut found %d" % (n, old[:80], c))
    html = html.replace(old, new, 1 if n == 1 else -1)
    print("OK  replace x%d" % c)

# ---- EDIT 1: 四键贴底 —— 去掉 absolute 兜底，交回 flex ----
do(
'''function kdV39PinBar() {
  var inner = document.querySelector("#topWrap .cl-inner");
  var bar = document.getElementById("btnBar");
  if (!inner || !bar) { return; }
  var bh = 0;
  try { bh = bar.offsetHeight || 0; } catch (e0) { bh = 0; }
  if (!bh) { return; }
  /* V42：再钉一道「左栏最低端」—— CSS 已经 !important 贴底，
     这里补 JS 兜底：万一某套主题/尺寸覆盖了带 #topWrap 前缀的规则，
     按钮会浮在半空，而这条内联样式不受选择器特异性影响。 */
  try {
    if (bar.style.position !== "absolute") { bar.style.position = "absolute"; }
    if (bar.style.bottom !== "0px") { bar.style.bottom = "0px"; }
    if (bar.style.left !== "0px") { bar.style.left = "0px"; }
    if (bar.style.right !== "0px") { bar.style.right = "0px"; }
  } catch (eP) {}
  var want = (bh + 6) + "px";
  if (inner.style.paddingBottom !== want) { try { inner.style.paddingBottom = want; } catch (e1) {} }
}''',
'''function kdV39PinBar() {
  /* H9/Android：四键用 flex 自然贴底（.cl-inner 是竖向 flex、#btnBar 是末子，
     已靠 CSS flex:0 0 10% 钉在左栏最底）。
     旧逻辑给 #btnBar 写 position:absolute 兜底，在横屏 .layout 旋转后会错位浮动，
     反而把键顶离底部。这里改为清掉内联 absolute，交回 CSS flex 处理。 */
  var inner = document.querySelector("#topWrap .cl-inner");
  var bar = document.getElementById("btnBar");
  if (bar) {
    try {
      bar.style.position = "";
      bar.style.bottom = "";
      bar.style.left = "";
      bar.style.right = "";
      bar.style.marginTop = "auto";   /* 末子顶到底，绝不被内容挤走 */
    } catch (e) {}
  }
  if (inner) { try { inner.style.paddingBottom = ""; } catch (e1) {} }
}''')

# ---- EDIT 2a: applyFit 入口服零互递归闸（非铺满补差触发时）----
do(
'''function applyFit(opts) {
  var force = (opts && opts.force);''',
'''function applyFit(opts) {
  var force = (opts && opts.force);
  /* V44：非「铺满补差」触发的 applyFit（用户保存/旋转/resize）重置互递归闸，
     让一轮铺满最多再补 3 次，彻底杜绝点【保存设置】后主线程被顶死（H9 卡死根因）。 */
  if (!(opts && opts._fill)) { _kdFillChain = 0; }''')

# ---- EDIT 2b: kdEnsureFill 重调度加互递归上限闸 ----
do(
'''    if (changed && !_kdFillPend) {
      _kdFillPend = true;
      setTimeout(function () { _kdFillPend = false; try { applyFit({ force: true }); } catch (eAf) {} }, 0);
    }''',
'''    if (changed && _kdFillChain < 3) {
      _kdFillChain++;
      setTimeout(function () { try { applyFit({ force: true, _fill: true }); } catch (eAf) {} }, 30);
    } else if (_kdFillChain >= 3) {
      _kdFillChain = 0;   /* 连续 3 轮仍铺不满 -> 放弃，避免主线程被互递归顶死 */
    }''')

# ---- EDIT 2c: 声明 _kdFillChain ----
do(
'''var _kdFillPend = false;   /* V38：铺满补差的重入闸，切断与 applyFit 的互递归 */''',
'''var _kdFillPend = false;   /* V38：铺满补差的重入闸，切断与 applyFit 的互递归 */
var _kdFillChain = 0;      /* V44：applyFit<->kdEnsureFill 互递归上限闸，防卡死 */''')

# ---- EDIT 3a: 新闻抓取默认 5 分钟 ----
do(
'''var DEF_FETCH_MIN_INTERVAL = 180;    /* V41：新闻整轮刷新间隔(秒)，默认 3 分钟 —— 后台把全部 RSS 源拉一遍 */''',
'''var DEF_FETCH_MIN_INTERVAL = 300;    /* V44：新闻整轮刷新间隔(秒)，默认 5 分钟 —— 后台把全部 RSS 源拉一遍 */''')

# ---- EDIT 3b: 更新提示文案 3 分钟 -> 5 分钟 ----
do(
'''    <div class="hint">新闻默认每 <b>3 分钟</b>（180 秒）在后台把下面「新闻源」里的<b>全部</b>源拉一遍。各源并行抓取，并按「源」轮流上首页 —— 哪一家条数多都不会把版面占满，也不会把别家挤掉。</div>''',
'''    <div class="hint">新闻默认每 <b>5 分钟</b>（300 秒）在后台把下面「新闻源」里的<b>全部</b>源拉一遍（各源并行、无条数上限、只显示今天、按发布时间先后）。各源并行抓取，并按「源」轮流上首页 —— 哪一家条数多都不会把版面占满，也不会把别家挤掉。</div>''')

# ---- EDIT 4: 音乐 —— 有原生桥时优先交给原生 MediaPlayer 播 ----
do(
'''function musicStartLoop() {
  var c = muCfg(), i;
  if (!_muList.length) { muLoadFolder(c.dir); }
  if (!_muList.length) {
    for (i = 0; i < MU_FALLBACK_DIRS.length && !_muList.length; i++) {
      if (MU_FALLBACK_DIRS[i] === c.dir) { continue; }
      if (muLoadFolder(MU_FALLBACK_DIRS[i]) > 0) { c.dir = MU_FALLBACK_DIRS[i]; muSave(c); }
    }
  }
  if (!_muList.length) {
    /* 页面扫不到目录（目录不存在，或老 WebView 读不了本地文件）→ 退原生 MediaPlayer。 */
    if (muHasBridge() && window.KindleBridge.musicPlay) {
      try {
        muPushPlaylist();
        window.KindleBridge.musicPlay(JSON.stringify({ dir: c.dir, playlist: c.playlist, mode: c.mode }));
        muMsg("已交给原生播放器：" + c.dir);
        try { kdToast("MUSIC：开始播放 " + c.dir); } catch (eT0) {}
        musicSyncState();
        return;
      } catch (eP) {}
    }
    muMsg("没找到可播放的音乐，请到设置里用【浏览】指定一个放音乐的文件夹");
    try { kdToast("MUSIC：没找到音乐，请先到设置里指定文件夹"); } catch (eT1) {}
    return;
  }''',
'''function musicStartLoop() {
  var c = muCfg(), i;
  /* H9/Android：有原生桥就直接交给原生 MediaPlayer 播（它能直接读 file://，
     而页面内 <audio> 在 WebView 里常被 file:// 跨域访问拦掉、点了没声）。
     无桥（纯浏览器）才走页面 <audio> 路径。 */
  if (muHasBridge() && window.KindleBridge.musicPlay) {
    try {
      muPushPlaylist();
      window.KindleBridge.musicPlay(JSON.stringify({ dir: c.dir, playlist: c.playlist, mode: c.mode }));
      muMsg("已交给原生播放器：" + c.dir);
      try { kdToast("MUSIC：开始播放 " + c.dir); } catch (eT0) {}
      musicSyncState();
      return;
    } catch (eP) {}
  }
  if (!_muList.length) { muLoadFolder(c.dir); }
  if (!_muList.length) {
    for (i = 0; i < MU_FALLBACK_DIRS.length && !_muList.length; i++) {
      if (MU_FALLBACK_DIRS[i] === c.dir) { continue; }
      if (muLoadFolder(MU_FALLBACK_DIRS[i]) > 0) { c.dir = MU_FALLBACK_DIRS[i]; muSave(c); }
    }
  }
  if (!_muList.length) {
    muMsg("没找到可播放的音乐，请到设置里用【浏览】指定一个放音乐的文件夹");
    try { kdToast("MUSIC：没找到音乐，请先到设置里指定文件夹"); } catch (eT1) {}
    return;
  }''')

# ---- EDIT 4b: muSmartClick —— 有桥时统一走原生 ----
do(
'''function muSmartClick() {
  var a = muAudioEl();
  if (a && a.src) {
    if (a.paused) { try { a.play(); } catch (e0) {} } else { try { a.pause(); } catch (e1) {} }
    musicSyncState();
    return;
  }
  var last = "";
  try { last = storeGet("kd_mu_last") || ""; } catch (e2) { last = ""; }
  if (last) {
    muPlayFile(last);
    try { kdToast("MUSIC：继续播放 " + muBaseName(last)); } catch (e3) {}
    return;
  }
  musicStartLoop();
}''',
'''function muSmartClick() {
  var a = muAudioEl();
  /* 正在用页面 <audio> 播 -> 暂停（仅无桥环境会走到这里） */
  if (a && a.src && !a.paused) {
    try { a.pause(); } catch (e1) {}
    musicSyncState();
    return;
  }
  /* 有原生桥时一律走原生（能读 file://、后台可播）；否则用页面 <audio> 续播/开播 */
  if (muHasBridge() && window.KindleBridge.musicPlay) {
    musicStartLoop();
    return;
  }
  if (a && a.src) { try { a.play(); } catch (e0) {} musicSyncState(); return; }
  var last = "";
  try { last = storeGet("kd_mu_last") || ""; } catch (e2) { last = ""; }
  if (last) {
    muPlayFile(last);
    try { kdToast("MUSIC：继续播放 " + muBaseName(last)); } catch (e3) {}
    return;
  }
  musicStartLoop();
}''')

# ---- EDIT 5: 新闻源清单自身可滚 + H9 触摸滚动 ----
do(
'''.modal { will-change: transform; }''',
'''.modal { will-change: transform; }
/* V44：新闻源清单自身可滚，长清单不再撑爆整页设置；H9 触摸滚动更顺 */
#rssList { max-height: 60vh; overflow-y: auto; -webkit-overflow-scrolling: touch; touch-action: pan-y; }
html.kdl-h9 #settingsMask { -webkit-overflow-scrolling: touch; touch-action: pan-y; }''')

# ---- 备份 + 写回 ----
with io.open(BAK, "w", encoding="utf-8") as f:
    f.write(orig)
with io.open(SRC, "w", encoding="utf-8") as f:
    f.write(html)

print("DONE. new length=%d (was %d), delta=%d" % (len(html), len(orig), len(html) - len(orig)))
