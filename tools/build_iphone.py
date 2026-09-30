import io, os, json, sys
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
PROJECT = _os.path.dirname(_HERE)

SP=_os.path.join(PROJECT,"build","httest")
inner=io.open(os.path.join(SP,"layout.html"),encoding="utf-8").read()
io.open(os.path.join(SP,"iphone_inner.html"),"w",encoding="utf-8").write(inner)

# 440x956 = iPhone 17 Pro Max / 16 Pro Max CSS viewport (primary target)
SIZES=[("pmax_p","iPhone 17 Pro Max portrait",440,956),
       ("pro_p","iPhone 17 Pro portrait",402,874),
       ("p16_p","iPhone 16 portrait",393,852),
       ("se_p","iPhone SE portrait",375,667),
       ("min_p","smallest legacy portrait",320,568),
       ("android","Android phone (Pixel)",412,915),
       ("pmax_l","iPhone 17 Pro Max landscape",956,440),
       ("ipad_p","iPad portrait",820,1180),
       ("ipad_l","iPad landscape",1180,820),
       ("laptop","Laptop 1366",1366,768),
       ("desktop","Desktop 1920",1920,1080)]

TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>pending</title>
<style>html,body{margin:0;background:#222}iframe{border:0;display:block}</style></head><body>
<iframe id="f" style="width:%(w)dpx;height:%(h)dpx" src="iphone_inner.html"></iframe>
<pre id="out"></pre>
<script>
var LABEL=%(label)s, tries=0;
var iv=setInterval(function(){
  tries++;
  var W=null; try{ W=document.getElementById('f').contentWindow; }catch(e){}
  if(W && W.__done){
    clearInterval(iv);
    var res=['=== '+LABEL+' — %(w)dx%(h)d (inner '+W.innerWidth+'x'+W.innerHeight+') — issues: '+W.__BAD+' ==='];
    W.__REPORT.forEach(function(l){ res.push(l); });
    document.title=(W.__BAD===0?'IPHONEOK':'IPHONEBAD')+' '+W.__BAD;
    document.getElementById('out').textContent='IPHONE_START\\n'+res.join('\\n')+'\\nIPHONE_END';
  } else if(tries>600){
    clearInterval(iv); document.title='IPHONEBAD timeout';
    document.getElementById('out').textContent='IPHONE_START\\nISSUE | '+LABEL+' never booted\\nIPHONE_END';
  }
},50);
</script></body></html>"""

for slug,label,w,h in SIZES:
    io.open(os.path.join(SP,"ip_%s.html"%slug),"w",encoding="utf-8").write(
        TPL % {"w":w,"h":h,"label":json.dumps(label)})

# ---------------------------------------------------------------------------
# PUBLISH to the directory the http server actually serves.
#
# These files were only ever written to the scratchpad root, while the server
# runs with --directory scratchpad\httest. The httest copies were published by
# hand, so they silently went stale: every audit run after 2026-09-16 17:57
# measured yesterday's build and reported passes for code that no longer
# existed. Publishing here, in the last build step, is what makes a stale
# audit impossible rather than merely unlikely.
# ---------------------------------------------------------------------------
HT = os.path.join(SP, "httest")
if not os.path.isdir(HT):
    os.makedirs(HT)
io.open(os.path.join(HT, "iphone_inner.html"), "w", encoding="utf-8").write(inner)
for slug, label, w, h in SIZES:
    io.open(os.path.join(HT, "ip_%s.html" % slug), "w", encoding="utf-8").write(
        TPL % {"w": w, "h": h, "label": json.dumps(label)})
print(" ".join(s[0] for s in SIZES))
print("published %d viewports + iphone_inner.html to httest" % len(SIZES))
