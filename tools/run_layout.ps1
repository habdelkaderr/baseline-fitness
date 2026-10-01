# Build and measure every viewport. Builds first: measuring whatever happened
# to be in the served folder is how this harness once audited a stale build.
$PROJ = Split-Path -Parent $PSScriptRoot
$BUILD= Join-Path $PROJ "build"
$edge="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

python "$PSScriptRoot\build_layout.py"
if(-not $?){ throw "build_layout.py failed" }
python "$PSScriptRoot\build_iphone.py"
if(-not $?){ throw "build_iphone.py failed" }

$slugs=@("pmax_p","pro_p","p16_p","se_p","min_p","android","pmax_l","ipad_p","ipad_l","laptop","desktop")
$tot=0
foreach($s in $slugs){
  $got=$false
  foreach($try in 1..3){
    $prof=Join-Path $BUILD ("lp_"+$s)
    if(Test-Path $prof){ Remove-Item -LiteralPath $prof -Recurse -Force -ErrorAction SilentlyContinue }
    & $edge --headless=new --disable-gpu --no-sandbox --user-data-dir="$prof" --hide-scrollbars --window-size=1960,1200 --virtual-time-budget=50000 --dump-dom "http://127.0.0.1:8801/ip_$s.html" 2>$null | Out-File (Join-Path $BUILD ("o_"+$s+".txt")) -Encoding utf8
    $t=Get-Content (Join-Path $BUILD ("o_"+$s+".txt")) -Raw
    if($t -match '(?s)<pre id="out">(.*?)</pre>'){
      $r=$matches[1] -replace '&lt;','<' -replace '&gt;','>' -replace '&amp;','&'
      if($r -notmatch 'never booted'){
        $got=$true
        (($r -split "`n" | Where-Object { $_ -match '^ISSUE|===|TOTAL ISSUES|AUDIT THREW' }) -join "  ")
        # A THROWN AUDIT MEASURES NOTHING, AND USED TO SAY NOTHING.
        # The filter above dropped "AUDIT THREW" because it does not start with
        # ISSUE, and a throw also means no "TOTAL ISSUES" line to add up - so a
        # run in which every viewport died printed a confident
        # "TOTAL RESPONSIVE ISSUES: 0". Count the throws, and refuse to treat a
        # missing total as a pass.
        $thrown = ([regex]::Matches($r,'AUDIT THREW')).Count
        if($thrown -gt 0){
          "  $s : AUDIT THREW x$thrown - measured nothing"
          $tot += $thrown
        }
        if($r -match 'TOTAL ISSUES: (\d+)'){ $tot += [int]$matches[1] }
        elseif($thrown -eq 0){
          "  $s : NO TOTAL LINE - measured nothing"
          $tot += 1
        }
        break
      }
    }
  }
  if(-not $got){ "$s : harness timeout"; $tot+=1 }
}
""
"TOTAL RESPONSIVE ISSUES: $tot"
