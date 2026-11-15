# lt.ps1 — sobe, derruba ou consulta o servidor local do LanguageTool.
# Uso: powershell -File .\scripts\lt.ps1 -Acao start [-Porta 8081]
param(
  [ValidateSet("start", "stop", "status")][string]$Acao = "start",
  [int]$Porta = 8081
)
$ErrorActionPreference = "Stop"

$homeLt = if ($env:PANDITA_LT_HOME) { $env:PANDITA_LT_HOME } else { Join-Path $env:LOCALAPPDATA "pandita\languagetool" }
$jar = Get-ChildItem (Join-Path $homeLt "LanguageTool-*\languagetool-server.jar") -ErrorAction SilentlyContinue |
       Select-Object -First 1
$logFile = Join-Path $homeLt "lt.log"
$url = "http://localhost:$Porta/v2/languages"

function Testar {
  try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
    return $r.StatusCode -eq 200
  } catch { return $false }
}

function AcharJava {
  if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
    return (Join-Path $env:JAVA_HOME "bin\java.exe")
  }
  $c = Get-Command java -ErrorAction SilentlyContinue
  if ($c -and $c.Source -notlike "*WindowsApps*") { return $c.Source }
  $j = Get-ChildItem "C:\Program Files\Eclipse Adoptium\*\bin\java.exe",
                      "C:\Program Files\Java\*\bin\java.exe" -ErrorAction SilentlyContinue |
       Select-Object -First 1
  if ($j) { return $j.FullName }
  return $null
}

switch ($Acao) {
  "status" {
    if (Testar) { Write-Host "LanguageTool no ar em http://localhost:$Porta" }
    else { Write-Host "LanguageTool parado." }
  }
  "start" {
    if (Testar) { Write-Host "Já está no ar em http://localhost:$Porta"; break }
    if (-not $jar) {
      throw "LanguageTool não encontrado em $homeLt. Baixe em https://languagetool.org/download/ e extraia aí."
    }
    $java = AcharJava
    if (-not $java) { throw "Java não encontrado. Instale um JRE 17+ ou defina JAVA_HOME." }

    # Win32_Process cria o servidor desacoplado: o script retorna sem esperar o Java.
    # O cmd /c existe só para o ">" gravar o log. Sem --public: o servidor escuta só nesta máquina.
    $linha = "cmd.exe /c `"`"$java`" -Xmx1g -jar `"$($jar.FullName)`" --port $Porta > `"$logFile`" 2>&1`""
    $oculto = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0 }
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
      CommandLine = $linha; CurrentDirectory = $jar.Directory.FullName; ProcessStartupInformation = $oculto
    }
    if ($r.ReturnValue -ne 0) { throw "Não consegui iniciar o Java (código $($r.ReturnValue))." }

    for ($i = 0; $i -lt 40; $i++) {
      Start-Sleep -Milliseconds 800
      if (Testar) { Write-Host "LanguageTool no ar em http://localhost:$Porta"; break }
    }
    if (-not (Testar)) { throw "Não subiu. Veja $logFile" }
  }
  "stop" {
    # Para pelo nome do servidor, não por um número de processo guardado: o número pode ter virado outro programa.
    Get-CimInstance Win32_Process -Filter "Name='java.exe'" -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -like "*languagetool-server.jar*" } |
      ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "LanguageTool parado."
  }
}
