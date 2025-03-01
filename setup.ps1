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

# --- Install Python Modules using current Python environment ---
Set-Location -Path "backend"
Write-Host "Installing Python dependencies from requirements.txt in the current Python environment..."

# Get current Python executable path (works with venv/conda)
$pythonPath = & {
    # Try to detect if we're in a virtual environment
    if ($env:VIRTUAL_ENV) {
        # We're in a venv
        Join-Path -Path $env:VIRTUAL_ENV -ChildPath "Scripts\python.exe"
    }
    elseif ($env:CONDA_PREFIX) {
        # We're in a conda environment
        Join-Path -Path $env:CONDA_PREFIX -ChildPath "python.exe"
    }
    else {
        # Use system Python
        "python"
    }
}

Write-Host "Using Python interpreter: $pythonPath"

# Install dependencies using requirements.txt
& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Python dependencies from requirements.txt. Please check the error messages above and ensure requirements.txt exists."
    exit 1
}

Write-Host "Python dependencies installed successfully from requirements.txt."

# --- Install Node Modules ---
Set-Location -Path "..\frontend-for-keylogger"
Write-Host "Installing Node.js dependencies..."

npm install
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Node.js dependencies. Exit code: $($LASTEXITCODE)"
    exit 1
} else {
    Write-Host "Node.js dependencies installed successfully."
}

# --- Create .env file for backend if it doesn't exist ---
Set-Location -Path "..\backend"
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file with default values..."
    @"
MONGO_URI=mongodb://localhost:27017/
MASTER_KEY=default_master_key_please_change_this
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Created .env file. Please update the MASTER_KEY value for security."
}

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
Write-Host ""
Write-Host "IMPORTANT: Update the MASTER_KEY in the backend/.env file before using the application."
