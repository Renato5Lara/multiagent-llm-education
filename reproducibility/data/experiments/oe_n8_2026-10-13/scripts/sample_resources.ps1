param([string]$Out, [int]$Every = 30)
# Muestreo ligero de recursos del host durante una campaña: memoria libre, carga de CPU y memoria de la VM de Docker/WSL (vmmem*).
$ci = [System.Globalization.CultureInfo]::InvariantCulture
"t_utc,free_mem_gb,cpu_load_pct,vmmem_mb" | Out-File $Out -Encoding ascii
while ($true) {
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
    $d = (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'vmmem*' } | Measure-Object WorkingSet64 -Sum).Sum / 1MB
    [string]::Format($ci, "{0},{1:F2},{2:F1},{3:F0}", (Get-Date).ToUniversalTime().ToString('s'), ($os.FreePhysicalMemory / 1MB), $cpu, $d) | Out-File $Out -Append -Encoding ascii
    Start-Sleep $Every
}
