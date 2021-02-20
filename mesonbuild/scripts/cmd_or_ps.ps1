# Copyied from GStreamer project
# Author: Seungha Yang <seungha.yang@navercorp.com>

$i=1
$ppid=(gwmi win32_process -Filter "processid='$pid'").parentprocessid
$pname=(Get-Process -id $ppid).Name
While($true) {
  if($pname -eq "cmd" -Or $pname -eq "powershell") {
    Write-Host ("{0}.exe" -f $pname)
    Break
  }

  # 10 times iteration seems to be sufficient
  if($i -gt 10) {
    Break
  }

  # not found yet, find grand parant
  $ppid=(gwmi win32_process -Filter "processid='$ppid'").parentprocessid
  $pname=(Get-Process -id $ppid).Name
  $i++
}
