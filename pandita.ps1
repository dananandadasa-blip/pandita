# pandita.ps1 — atalho opcional no Windows: acha um Python e chama o CLI.
# Uso: powershell -File .\pandita.ps1 <subcomando> [args]
# No macOS/Linux, chame direto: python3 scripts/pandita.py …
$ErrorActionPreference = 'Stop'

$py = $null
$prefixo = @()

foreach ($nome in @('python', 'python3')) {
  $cmd = Get-Command $nome -ErrorAction SilentlyContinue
  # o alias da Microsoft Store não é um Python de verdade
  if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $py = $cmd.Source; break }
}

if (-not $py) {
  $cmd = Get-Command py -ErrorAction SilentlyContinue
  if ($cmd) { $py = $cmd.Source; $prefixo = @('-3') }
}

if (-not $py -and $env:DSH_PYTHON -and (Test-Path $env:DSH_PYTHON)) { $py = $env:DSH_PYTHON }

if (-not $py) {
  $r = Get-ChildItem "$HOME\.dsh\dsh-runtimes\*\dependencies\python\python.exe" -ErrorAction SilentlyContinue |
       Select-Object -First 1
  if ($r) { $py = $r.FullName }
}

if (-not $py) { throw 'Python não encontrado. Instale Python 3.9+ ou chame scripts\pandita.py direto.' }

$argumentos = @($prefixo) + @('-X', 'utf8', "$PSScriptRoot\scripts\pandita.py") + $args
& $py @argumentos
exit $LASTEXITCODE
