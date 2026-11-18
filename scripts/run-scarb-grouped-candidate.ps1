param([Parameter(Mandatory)][string]$Manifest,[Parameter(Mandatory)][string]$ApprovedManifestSha256,[Parameter(Mandatory)][string]$State,[string]$FixtureResponses,[string]$ApprovedFixtureResponsesSha256,[string]$FixtureNow,[string]$FixtureCompletedAt)
$ErrorActionPreference='Stop'
if($ApprovedManifestSha256 -notmatch '^[a-f0-9]{64}$' -or (Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash -ine $ApprovedManifestSha256){throw 'Exact manifest mismatch'}
$entry=Join-Path $PSScriptRoot 'launch_scarb_grouped_candidate.py'
$python='C:\Program Files\Python312\python.exe'
if($FixtureResponses){
 if($ApprovedFixtureResponsesSha256 -notmatch '^[a-f0-9]{64}$' -or (Get-FileHash -LiteralPath $FixtureResponses -Algorithm SHA256).Hash -ine $ApprovedFixtureResponsesSha256){throw 'Injected response mismatch'}
 if(-not(Test-Path -LiteralPath (Join-Path $State 'SYNTHETIC_GROUPED_ACCOUNTING_ONLY'))){throw 'Disposable state required'}
 & $python -I -S $entry --manifest $Manifest --manifest-sha256 $ApprovedManifestSha256 --state $State --fixture-responses $FixtureResponses --fixture-responses-sha256 $ApprovedFixtureResponsesSha256 --fixture-now $FixtureNow --fixture-completed-at $FixtureCompletedAt
 if($LASTEXITCODE -ne 0){throw 'Held/refused; no automatic retry'}
 return
}
# No real secret lookup until disabled-by-default exact private gate and full
# manifest/code/funding/source preflight succeed in the child.
& $python -I -S $entry --preflight-only --manifest $Manifest --manifest-sha256 $ApprovedManifestSha256 --state $State
if($LASTEXITCODE -ne 0){throw 'Preflight refused; no credentials accessed'}
if([System.Security.Principal.WindowsIdentity]::GetCurrent().Name -ine 'JUSTIN-PERSONAL\justinfisher'){throw 'Wrong Windows identity'}
$expected=Join-Path $env:LOCALAPPDATA 'ScarbTO\voice-private'
if([IO.Path]::GetFullPath($State) -ine [IO.Path]::GetFullPath($expected)){throw 'Wrong protected state root'}
$secure=ConvertTo-SecureString (Get-Content -LiteralPath (Join-Path $expected 'scarb-api-key.dpapi') -Raw)
try {
 $psi=New-Object System.Diagnostics.ProcessStartInfo
 $psi.FileName=$python;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
 $psi.Arguments='-I -S "'+$entry+'" --manifest "'+$Manifest+'" --manifest-sha256 '+$ApprovedManifestSha256+' --state "'+$State+'"'
 $psi.EnvironmentVariables['OPENAI_API_KEY']=(New-Object System.Net.NetworkCredential('', $secure)).Password
 $psi.EnvironmentVariables['OPENAI_ORG_ID']='org-EIn1HXt0x19rnOSvte7dVrB9';$psi.EnvironmentVariables['OPENAI_PROJECT_ID']='proj_ZiSvyeNLotSbqtH2vDEKqNxx';$psi.EnvironmentVariables['SCARB_AI_ENABLE']='1'
 $child=[System.Diagnostics.Process]::Start($psi);$psi.EnvironmentVariables.Remove('OPENAI_API_KEY')
 $out=$child.StandardOutput.ReadToEndAsync();$err=$child.StandardError.ReadToEndAsync();$child.WaitForExit()
 $discardOut=$out.GetAwaiter().GetResult();$discardErr=$err.GetAwaiter().GetResult();$discardOut=$null;$discardErr=$null
 if($child.ExitCode -ne 0){throw 'Grouped run held or failed; no automatic retry'}
 Write-Output 'Grouped review recorded; no registry enrollment or publication.'
}finally{$secure.Dispose();if($psi){$psi.EnvironmentVariables.Remove('OPENAI_API_KEY')}}
