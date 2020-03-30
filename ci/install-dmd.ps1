param (
    [string]$Version = $null
)
Set-StrictMode -Version latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

echo "=== Installing DMD ==="

# default installation directory
$dmd_install = "C:\D"
$dmd_version_file = "C:\cache\DMD_LATEST"

if (!$Version) {
    #echo "Fetching latest DMD version..."
    $dmd_latest_url = "http://downloads.dlang.org/releases/LATEST"
    $retries = 10
    echo ('Downloading {0} ...' -f $dmd_latest_url)
    for ($i = 1; $i -le $retries; $i++) {
        try {
            [system.io.directory]::CreateDirectory((Split-Path -parent $dmd_version_file)) > $null
            Invoke-WebRequest -URI $dmd_latest_url -OutFile $dmd_version_file
            echo '... DONE'
            break
        } catch [net.WebException] {
            if ($i -eq $retries) {
                break
            }
            $backoff = (10 * $i) # backoff 10s, 20s, 30s...
            echo ('{0}: {1}' -f $dmd_latest_url, $_.Exception.Message)
            echo ('Retrying in {0}s...' -f $backoff)
            Start-Sleep -m ($backoff * 1000)
        } catch {
            throw
        }
    }
    if (Test-Path $dmd_version_file) {
        $dmd_version = Get-Content -Path $dmd_version_file
    } else {
        throw "Failed to resolve latest DMD version"
    }
} else {
    $dmd_version = $Version
}
$dmd_url = "http://downloads.dlang.org/releases/2.x/$dmd_version/dmd.$dmd_version.windows.zip"
$dmd_filename = [System.IO.Path]::GetFileName($dmd_url)
$dmd_archive = Join-Path ($env:temp) $dmd_filename

echo "Downloading $dmd_filename..."
$retries = 10
for ($i = 1; $i -le $retries; $i++) {
    try {
        (New-Object net.webclient).DownloadFile($dmd_url, $dmd_archive)
        break
    } catch [net.WebException] {
        if ($i -eq $retries) {
            throw # fail on last retry
        }
        $backoff = (10 * $i) # backoff 10s, 20s, 30s...
        echo ('{0}: {1}' -f $dmd_url, $_.Exception.Message)
        echo ('Retrying in {0}s...' -f $backoff)
        Start-Sleep -m ($backoff * 1000)
    }
}

echo "Extracting $dmd_filename..."
Expand-Archive $dmd_archive -Force -DestinationPath $dmd_install

# add to environment path
echo "Installing DMD..."
$dmd_bin = Join-Path $dmd_install "dmd2\windows\bin"
$Env:Path = $Env:Path + ";" + $dmd_bin

echo "Testing DMD..."
& dmd.exe --version
