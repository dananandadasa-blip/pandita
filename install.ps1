# Instala ou atualiza a skill pandita no diretório de skills de um agente.
# Uso: .\install.ps1 -Destino "$HOME\.claude\skills\pandita"
param(
  [string]$Destino = (Join-Path $HOME ".claude\skills\pandita")
)

$ErrorActionPreference = "Stop"
$origem = $PSScriptRoot
New-Item -ItemType Directory -Force -Path $Destino | Out-Null

# O destino é a pasta-mãe: assim a segunda instalação atualiza, em vez de criar scripts\scripts.
foreach ($item in @("SKILL.md", "README.md", "LICENSE", "requirements.txt", "pandita.ps1", "referencias", "scripts")) {
  Copy-Item -Recurse -Force (Join-Path $origem $item) $Destino
}
# Arquivos da casa: só na primeira vez, para não apagar o que você editou.
foreach ($item in @("PADRAO.md", "glossario.csv", "config.json", "ignorar.txt")) {
  if (Test-Path (Join-Path $Destino $item)) { Write-Host "mantido: $item" }
  else { Copy-Item (Join-Path $origem $item) $Destino }
}
Get-ChildItem $Destino -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Write-Host "pandita instalado em: $Destino"
Write-Host "Para ler e gerar .docx: pip install -r `"$Destino\requirements.txt`""
Write-Host "Para usar no DeepSeek Harness, copie para .dsh/skills/pandita."
