param([Parameter(Mandatory)][string]$Manifest,[Parameter(Mandatory)][string]$ApprovedManifestSha256,[Parameter(Mandatory)][string]$State,[Parameter(Mandatory)][string]$FixtureResponses,[Parameter(Mandatory)][string]$ApprovedFixtureResponsesSha256,[Parameter(Mandatory)][string]$FixtureNow,[Parameter(Mandatory)][string]$FixtureCompletedAt)
$ErrorActionPreference='Stop'
# Disposable offline launcher only. No DPAPI, environment-secret lookup or real
# one-shot config path. The reviewed production launcher remains unchanged.
foreach($pair in @(@($Manifest,$ApprovedManifestSha256),@($FixtureResponses,$ApprovedFixtureResponsesSha256))){if($pair[1] -notmatch '^[a-f0-9]{64}$' -or (Get-FileHash -LiteralPath $pair[0] -Algorithm SHA256).Hash -ine $pair[1]){throw 'Exact injected input mismatch'}}
if(-not(Test-Path -LiteralPath (Join-Path $State 'SYNTHETIC_GROUPED_ACCOUNTING_ONLY'))){throw 'Disposable state marker required'}
$entry=Join-Path $PSScriptRoot 'launch_scarb_grouped_candidate.py'
& 'C:\Program Files\Python312\python.exe' -I -S $entry --manifest $Manifest --manifest-sha256 $ApprovedManifestSha256 --state $State --fixture-responses $FixtureResponses --fixture-responses-sha256 $ApprovedFixtureResponsesSha256 --fixture-now $FixtureNow --fixture-completed-at $FixtureCompletedAt
if($LASTEXITCODE -ne 0){throw 'Grouped candidate held or refused; no automatic retry'}
