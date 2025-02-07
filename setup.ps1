# Script to setup environment and provide instructions for running frontend, keylogger, and API

# --- Check and Install Prerequisites ---

# Function to check and install a package using winget
function Check-And-Install {
    param(
        [string]$PackageName,
        [string]$WingetId
    )
    if (-not (Get-Command $PackageName -ErrorAction SilentlyContinue)) {
        Write-Host "$PackageName not found. Installing..."
        try {
            winget install $WingetId -e --accept-package-agreements --accept-source-agreements
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


# Check and install npm (Node.js)
Check-And-Install -PackageName "npm" -WingetId "OpenJS.NodeJS.LTS" # Or OpenJS.NodeJS.LTS for LTS version

# Check and install Python
Check-And-Install -PackageName "python" -WingetId "Python.Python.3.10" # installs latest python 3,  consider Python.Python.3.11 if you need a specific one

#Check and install Mongodb server

Check-And-Install -PackageName "mongod" -WingetId "MongoDB.Server"
# Start-Service -Name "MongoDB"
# Define the MongoDB service name
$mongoService = "MongoDB"

# Check if the MongoDB service is running
$service = Get-Service -Name $mongoService -ErrorAction SilentlyContinue

if ($service -and $service.Status -eq "Running") {
    Write-Output "MongoDB is already running."
} else {
    Write-Output "MongoDB is not running. Starting it now..."
    
    # Start MongoDB service
    Start-Service -Name $mongoService
    
    # Wait for a few seconds and check again
    Start-Sleep -Seconds 3
    $service = Get-Service -Name $mongoService -ErrorAction SilentlyContinue

    if ($service.Status -eq "Running") {
        Write-Output "MongoDB started successfully."
    } else {
        Write-Output "Failed to start MongoDB. Check service logs for details."
    }
}
# --- Navigate to Backend and Install Python Modules ---

# Store the current directory
$originalDirectory = Get-Location

# Navigate to the backend directory
Set-Location -Path "backend"  # Assuming 'backend' is a direct subdirectory

# Check if we successfully changed directory
if (-not (Test-Path ".")) {
  Write-Error "Error: Could not navigate to the 'backend' directory.  Ensure it exists."
  exit 1
}


# Install Python modules using pip (more robust error handling)
$pythonModules = @(
    "pynput",
    "pymongo",
    "Flask",
    "python-dotenv",  # If you plan to use .env files
    "flask_cors",
    "bson" #bson may not be installed on its own, it may be a part of pymongo, but this wont hurt
)

foreach ($module in $pythonModules) {
    Write-Host "Installing $module..."
    $process = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", $module -PassThru -Wait -NoNewWindow
    if (-not $process.ExitCode -eq 0) {
        Write-Error "Failed to install $module.  Check your Python and pip installation."
        exit 1
    }
}



# --- Navigate to Frontend and Install Node Modules ---

Set-Location -Path $originalDirectory #Return to parent
Set-Location -Path "frontend-for-keylogger" # Go into front end folder

# Check if we successfully changed directory
if (-not (Test-Path ".")) {
  Write-Error "Error: Could not navigate to the 'frontend-for-keylogger' directory.  Ensure it exists."
  exit 1
}


Write-Host "Installing Node modules..."
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm install" -Wait -NoNewWindow -PassThru
  if ($process.ExitCode -ne 0) {
    Write-Error "npm install failed.  Check for errors in the output above."
    exit 1
}

# --- Provide Instructions ---

Set-Location -Path $originalDirectory  # Go back to the original directory

Write-Host ""
Write-Host "--- Setup Complete! ---"
Write-Host ""
Write-Host "To start the application, open three separate terminal windows/tabs and run the following commands:"
Write-Host ""
Write-Host "1. Start Frontend (in 'frontend-for-keylogger' folder):" -ForegroundColor Green
Write-Host "   PS > cd frontend-for-keylogger"
Write-Host "   PS frontend-for-keylogger> npm start" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Start Keylogger (in root folder):" -ForegroundColor Green
Write-Host "   PS > python -u .\backend\main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Start API Endpoint (in root folder):" -ForegroundColor Green
Write-Host "   PS > python -u .\backend\app.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "Make sure MongoDB server is running before starting the keylogger and API." -ForegroundColor Magenta
Write-Host "You can usually start it with:  Start-Service -Name MongoDB" -ForegroundColor Magenta
Write-Host "If it is not MongoDB try checking the service name using: Get-Service | Where-Object {$_.Name -like '*Mongo*'}" -ForegroundColor Magenta
Write-Host ""