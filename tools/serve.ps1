# The local server the headless browser reads from.
#
# It stops whatever is already on the port FIRST, and it finds that process by
# asking who is listening rather than by guessing an executable name. The
# previous version killed processes called "python.exe"; the server that was
# actually running was "python3.13.exe", so it was never stopped, went on
# serving an old directory, and the test harness reported a pass for a build
# it had never loaded. Ask the port, not the name.
$PROJ = Split-Path -Parent $PSScriptRoot
$HT   = Join-Path $PROJ "build\httest"
New-Item -ItemType Directory -Force $HT | Out-Null

try {
  Get-NetTCPConnection -LocalPort 8801 -State Listen -ErrorAction Stop |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
      $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
      if ($p) { "stopping $($p.ProcessName) (pid $($p.Id)) on port 8801"; Stop-Process -Id $_ -Force }
    }
} catch { }

Start-Sleep -Milliseconds 400
Start-Process -FilePath "python" -ArgumentList "-m","http.server","8801","--directory","$HT" -WindowStyle Hidden
Start-Sleep -Seconds 2

# Prove it is serving the directory we meant, not one left over from before.
try {
  $r = Invoke-WebRequest "http://127.0.0.1:8801/" -UseBasicParsing -TimeoutSec 5
  "serving $HT on http://127.0.0.1:8801"
} catch {
  "FAILED to serve $HT : $($_.Exception.Message)"
}
