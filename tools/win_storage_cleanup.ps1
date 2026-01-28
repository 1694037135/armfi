param(
    [switch]$CleanTemp,
    [switch]$ClearRecycle,
    [switch]$ReportAppDuplicates,
    [switch]$ReportInstallerDuplicates,
    [switch]$AutoDeleteInstallerDuplicates
)
if ($PSBoundParameters.Count -eq 0) {
    $CleanTemp = $true
    $ClearRecycle = $true
    $ReportAppDuplicates = $true
    $ReportInstallerDuplicates = $true
}
function GetDriveFree {
    Get-PSDrive C,D | Select-Object Name, @{n="FreeMB";e={[math]::Round(($_.Free/1MB),2)}}
}
function CleanUserTemp {
    $p = "$env:TEMP\*"
    try { Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue } catch {}
}
function ClearBin {
    try { Clear-RecycleBin -Force -ErrorAction SilentlyContinue } catch {}
}
function FindDuplicateInstalls {
    $keys = @(
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    $apps = Get-ItemProperty $keys -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } | Select-Object @{n="Name";e={$_.DisplayName}}, @{n="Location";e={$_.InstallLocation}}, @{n="Uninstall";e={$_.UninstallString}}
    $apps = $apps | Where-Object { $_.Location -and $_.Location -match "^[A-Za-z]:" }
    $dup = $apps | Group-Object Name | Where-Object { $_.Count -gt 1 -and (($_.Group | ForEach-Object { $_.Location.Substring(0,1) }) | Sort-Object -Unique).Count -gt 1 }
    $out = @()
    foreach ($g in $dup) {
        foreach ($i in $g.Group) {
            $out += [PSCustomObject]@{Name=$i.Name; Location=$i.Location; Uninstall=$i.Uninstall}
        }
    }
    $out
}
function FindInstallerDuplicates {
    $paths = @("$env:USERPROFILE\Downloads","C:\Users\Public\Downloads","D:\Downloads","D:\")
    $files = @()
    foreach ($p in $paths) {
        if (Test-Path $p) {
            $files += Get-ChildItem -Path $p -Recurse -File -Include *.exe, *.msi -ErrorAction SilentlyContinue
        }
    }
    $files = $files | Where-Object { $_.Length -gt 200MB }
    $items = @()
    foreach ($f in $files) {
        try {
            $h = Get-FileHash -Path $f.FullName -Algorithm SHA256 -ErrorAction SilentlyContinue
            $items += [PSCustomObject]@{Name=$f.Name;FullName=$f.FullName;LengthMB=[math]::Round($f.Length/1MB,2);Hash=$h.Hash}
        } catch {}
    }
    $grouped = $items | Group-Object Hash | Where-Object { $_.Count -gt 1 }
    $grouped
}
Write-Output "=== Before Free (MB) ==="
GetDriveFree | Format-Table -AutoSize
if ($CleanTemp) { CleanUserTemp }
if ($ClearRecycle) { ClearBin }
Write-Output "=== After Free (MB) ==="
GetDriveFree | Format-Table -AutoSize
if ($ReportAppDuplicates) {
    Write-Output "=== Duplicate Installed Apps Across C/D ==="
    $d = FindDuplicateInstalls
    if (-not $d -or $d.Count -eq 0) { Write-Output "None" } else { $d | Format-Table -AutoSize }
}
if ($ReportInstallerDuplicates) {
    Write-Output "=== Duplicate Installers (>200MB) ==="
    $g = FindInstallerDuplicates
    if (-not $g -or $g.Count -eq 0) { Write-Output "None" } else {
        foreach ($grp in $g) {
            Write-Output ("---- " + $grp.Name)
            $grp.Group | Sort-Object LengthMB -Descending | ForEach-Object { Write-Output ("{0} MB | " + $_.FullName) -f $_.LengthMB }
            if ($AutoDeleteInstallerDuplicates) {
                $keep = $grp.Group | Sort-Object LengthMB -Descending | Select-Object -First 1
                $del = $grp.Group | Where-Object { $_.FullName -ne $keep.FullName }
                foreach ($x in $del) {
                    try { Remove-Item -Path $x.FullName -Force -ErrorAction SilentlyContinue } catch {}
                }
                Write-Output "Deleted duplicates for hash: $($grp.Name)"
            }
        }
    }
}
