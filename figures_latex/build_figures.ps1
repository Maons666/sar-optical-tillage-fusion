# build_figures.ps1 -- compile the standalone figure sources and copy the PDFs to ..\ (figures\)
#
#   .\build_figures.ps1              build every fig*.tex in this folder
#   .\build_figures.ps1 -Only fig09  build only the sources whose name contains "fig09"
#
# Auxiliary files go to .\_build so that the source folder stays clean.
param([string]$Only = '')

$src = $PSScriptRoot
$out = Join-Path $src '_build'
New-Item -ItemType Directory -Force $out | Out-Null
if (-not (Get-Command pdflatex -ErrorAction SilentlyContinue)) { $env:Path = "E:\TinyTeX\bin\windows;$env:Path" }

$files = Get-ChildItem $src -Filter 'fig*.tex' |
    Where-Object { $_.Name -ne 'figstyle.tex' -and ($Only -eq '' -or $_.BaseName -like "*$Only*") }

Push-Location $src
foreach ($f in $files) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $engine = 'pdflatex'
    if (Get-Content $f.FullName -TotalCount 5 | Select-String -Quiet 'engine = lualatex') { $engine = 'lualatex' }
    & $engine -interaction=nonstopmode -halt-on-error "-output-directory=$out" $f.Name | Out-Null
    $code = $LASTEXITCODE
    $sw.Stop()
    if ($code -eq 0) {
        Copy-Item (Join-Path $out ($f.BaseName + '.pdf')) (Join-Path $src '..') -Force
        "OK    {0,-34} {1,5:N1} s  ({2})" -f $f.Name, $sw.Elapsed.TotalSeconds, $engine
    } else {
        "FAIL  {0,-34} see _build\{1}.log" -f $f.Name, $f.BaseName
        Select-String -Path (Join-Path $out ($f.BaseName + '.log')) -Pattern '^!' -Context 0,3 | Select-Object -First 3 | ForEach-Object { $_.ToString() }
    }
}
Pop-Location
