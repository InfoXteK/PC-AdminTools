param($f)
$t=$null;$e=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($f,[ref]$t,[ref]$e)
if($e.Count){$e|Select-Object -First 8|ForEach-Object{"ERR line $($_.Extent.StartLineNumber): $($_.Message)"}}else{"PARSE OK"}
