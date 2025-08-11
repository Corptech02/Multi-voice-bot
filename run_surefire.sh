#!/bin/bash

# Script to run Surefire CRM with correct working directory

# Set the working directory to where the DLL and appsettings.json are located
cd /home/corp06/software_projects/UIGCRM/current/bin/Debug/net8.0

# Run Surefire using the dotnet executable
/home/corp06/.dotnet/dotnet Surefire.dll