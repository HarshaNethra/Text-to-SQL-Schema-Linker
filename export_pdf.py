import os
import subprocess

ps_script = """
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $docPath = (Resolve-Path "docs/Dataset Benchmark Report/Spider Dataset Report.docx").Path
    $pdfPath = (Resolve-Path "docs/Dataset Benchmark Report/Spider Dataset Report.pdf").Path
    Write-Output "Opening $docPath..."
    $doc = $word.Documents.Open($docPath)
    $wdFormatPDF = 17
    Write-Output "Saving to $pdfPath..."
    $doc.SaveAs([ref]$pdfPath, [ref]$wdFormatPDF)
    $doc.Close([ref]$false)
    Write-Output "PDF Export Successful!"
} catch {
    Write-Output "Error: $_"
} finally {
    $word.Quit()
}
"""

with open("export_pdf.ps1", "w", encoding="utf-8") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "export_pdf.ps1"], capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)

if os.path.exists("export_pdf.ps1"):
    os.remove("export_pdf.ps1")
