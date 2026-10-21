$bad=0; $n=0
Get-ChildItem "$env:DUMP" -Filter *.ps1 | ForEach-Object {
  $t=$null;$e=$null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e)
  $n++
  if($e.Count){$bad++; Write-Output "PARSE ERROR $($_.Name): $($e[0].Message) line $($e[0].Extent.StartLineNumber)"}
}
Write-Output "parsed $n files, $bad with errors"
