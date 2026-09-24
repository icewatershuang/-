import re
p = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\assets\dashboard.html"
lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
def show(pat, maxn=40, cxt=0):
    rx = re.compile(pat)
    out=[]
    for i,l in enumerate(lines):
        if rx.search(l):
            out.append((i+1,l.strip()))
    print("### %r -> %d" % (pat,len(out)))
    for ln,t in out[:maxn]:
        s=t
        if len(s)>240: s=s[:240]+" ..."
        print("  L%d: %s" % (ln,s))
    return out

# HTML body structure: mainPage, layout, col-left, bottom-bar, btnBar, gear
show(r'id="mainPage"')
show(r'class="layout"|class="col-left"|class="col-right"|cl-inner|cr-wrap|cr-body')
show(r'bottom-bar|gear-mini|gear-row|id="btnBar"|class="btn-')
show(r'四个|虚拟|按键|底部四大|nav-')
# functions
show(r'function loadNews|function flushNewsPool|function attemptNews|function afterAllNews|function renderNews|function fitNewsToList')
show(r'function saveSettings|function saveRssRow|function bindQuickSave|function quickSaveLater')
show(r'_newsFlipTimer|autoFlip|function startNewsFlip|newsFlip')
show(r'function muPlay|function radioPlay|muPlay\(|\.play\(\)|audio\.play|muAudio')
show(r'fetchInterval|DEF_FETCH_MIN_INTERVAL|kdNewsDayRoll|newsPool')
