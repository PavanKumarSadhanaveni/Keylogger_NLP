# --- Function to Check and Install Prerequisites ---
function Check-And-Install {
    param(
        [string]$PackageName,
        [string]$WingetId
    )
    if (-not (Get-Command $PackageName -ErrorAction SilentlyContinue)) {
        Write-Host "$PackageName not found. Installing..."
        try {
            Start-Process -FilePath "winget" -ArgumentList "install", $WingetId, "-e", "--accept-package-agreements", "--accept-source-agreements" -NoNewWindow -Wait
            Write-Host "$PackageName installed successfully."
        }
        catch {
            Write-Error "Failed to install ${PackageName}: $($_.Exception.Message)"
            exit 1
        }
    } else {
        Write-Host "$PackageName is already installed."
    }
}

# --- Run Installations in Parallel ---
$tasks = @(
    {
        function Check-And-Install {
            param([string]$PackageName, [string]$WingetId)
            if (-not (Get-Command $PackageName -ErrorAction SilentlyContinue)) {
                Write-Host "$PackageName not found. Installing..."
                Start-Process -FilePath "winget" -ArgumentList "install", $WingetId, "-e", "--accept-package-agreements", "--accept-source-agreements" -NoNewWindow -Wait
                Write-Host "$PackageName installed successfully."
            }
        }
        Check-And-Install -PackageName "npm" -WingetId "OpenJS.NodeJS.LTS"
    },
    {
        function Check-And-Install {
            param([string]$PackageName, [string]$WingetId)
            if (-not (Get-Command $PackageName -ErrorAction SilentlyContinue)) {
                Write-Host "$PackageName not found. Installing..."
                Start-Process -FilePath "winget" -ArgumentList "install", $WingetId, "-e", "--accept-package-agreements", "--accept-source-agreements" -NoNewWindow -Wait
                Write-Host "$PackageName installed successfully."
            }
        }
        Check-And-Install -PackageName "python" -WingetId "Python.Python.3.10"
    },
    {
        function Check-And-Install {
            param([string]$PackageName, [string]$WingetId)
            if (-not (Get-Command $PackageName -ErrorAction SilentlyContinue)) {
                Write-Host "$PackageName not found. Installing..."
                Start-Process -FilePath "winget" -ArgumentList "install", $WingetId, "-e", "--accept-package-agreements", "--accept-source-agreements" -NoNewWindow -Wait
                Write-Host "$PackageName installed successfully."
            }
        }
        Check-And-Install -PackageName "mongod" -WingetId "MongoDB.Server"
    }
)

# Start parallel jobs
$jobs = foreach ($task in $tasks) {
    Start-Job -ScriptBlock $task
}

# Wait for all jobs to complete
$jobs | ForEach-Object { Receive-Job -Job $_ -Wait }

# --- Start MongoDB Service ---
$mongoService = "MongoDB"
$service = Get-Service -Name $mongoService -ErrorAction SilentlyContinue

if ($service -and $service.Status -ne "Running") {
    Write-Host "Starting MongoDB service..."
    Start-Service -Name $mongoService
    Start-Sleep -Seconds 3
    if ((Get-Service -Name $mongoService).Status -ne "Running") {
        Write-Error "Failed to start MongoDB. Check service logs."
        exit 1
    }
}

# --- Install Python Modules in a New Window ---
Set-Location -Path "backend"
Write-Host "Installing Python dependencies in a new window..."
Start-Process -FilePath "powershell.exe" -ArgumentList "-Command", "python -m pip install pynput pymongo Flask python-dotenv flask_cors bson" -WindowStyle Normal

# --- Install Node Modules in a New Window ---
Set-Location -Path "..\frontend-for-keylogger"
Write-Host "Installing Node.js dependencies in a new window..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c start cmd /k npm install" -WindowStyle Normal

# --- Final Instructions ---
Set-Location -Path ".."

Write-Host ""
Write-Host "--- Setup Complete! ---"
Write-Host "Run these commands to start the application:"
Write-Host ""
Write-Host "1. Start Frontend (in 'frontend-for-keylogger' folder):"
Write-Host "   PS > cd frontend-for-keylogger"
Write-Host "   PS frontend-for-keylogger> npm start"
Write-Host ""
Write-Host "2. Start Keylogger (in root folder):"
Write-Host "   PS > python -u .\backend\main.py"
Write-Host ""
Write-Host "3. Start API Endpoint (in root folder):"
Write-Host "   PS > python -u .\backend\app.py"
Write-Host ""
Write-Host "Make sure MongoDB server is running before starting the keylogger and API."
Write-Host "To check: Get-Service | Where-Object {$_.Name -like '*Mongo*'}"
