# Build the app from src/ and run the test suite.
$PROJ = Split-Path -Parent $PSScriptRoot
$SRC  = Join-Path $PROJ "src"
$BUILD= Join-Path $PROJ "build"
$HT   = Join-Path $BUILD "httest"
New-Item -ItemType Directory -Force $HT | Out-Null

$parts=@("p01","p02","p03","p03b","p04","p04b","p05","p06","p07","p08","p09","p10")
$out=New-Object System.Text.StringBuilder
foreach($n in $parts){ $null=$out.Append([IO.File]::ReadAllText((Join-Path $SRC ($n+".part")))) }
$app = Join-Path $BUILD "baseline.html"
[IO.File]::WriteAllText($app,$out.ToString(),(New-Object System.Text.UTF8Encoding($false)))
Copy-Item $app (Join-Path $HT "baseline.html") -Force
"built $([math]::Round((Get-Item $app).Length/1KB,1)) KB"

Push-Location $PSScriptRoot
python -W error::SyntaxWarning build_test.py | Out-Null
Pop-Location
Copy-Item (Join-Path $HT "test.html") (Join-Path $HT "test.html") -Force -ErrorAction SilentlyContinue

$edge="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$prof=Join-Path $BUILD "tp_run"
if(Test-Path $prof){ Remove-Item -LiteralPath $prof -Recurse -Force -ErrorAction SilentlyContinue }
& $edge --headless=new --disable-gpu --no-sandbox --user-data-dir="$prof" --hide-scrollbars --window-size=430,930 --virtual-time-budget=90000 --dump-dom "http://127.0.0.1:8801/test.html" 2>$null | Out-File (Join-Path $BUILD "o_test.txt") -Encoding utf8
$t=Get-Content (Join-Path $BUILD "o_test.txt") -Raw
if($t -match '<title>(.*?)</title>'){ "TITLE: $($matches[1])" }
if($t -match '(?s)<pre id="testout">(.*?)</pre>'){
  $r=$matches[1] -replace '&lt;','<' -replace '&gt;','>' -replace '&amp;','&'
  ($r -split "`n" | Where-Object { $_ -match '^FAIL|^THROW|^TOTAL' })
} else { "NO TEST OUTPUT" }
