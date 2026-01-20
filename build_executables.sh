#!/bin/bash
# Build script for creating PyInstaller executables

set -e

echo "Building AI File Organizer executables..."

# Install PyInstaller if not already installed
pip install pyinstaller

# Build CLI executable
echo "Building CLI executable..."
pyinstaller ai-file-organizer.spec --clean

# Build GUI executable
echo "Building GUI executable..."
pyinstaller ai-file-organizer-gui.spec --clean

echo "Build complete!"
echo "Executables are in the 'dist' directory:"
ls -lh dist/

# Create archive for distribution
echo "Creating distribution archive..."
cd dist
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    zip -r ai-file-organizer-windows.zip ai-file-organizer.exe ai-file-organizer-gui.exe
    echo "Created: ai-file-organizer-windows.zip"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    tar czf ai-file-organizer-macos.tar.gz ai-file-organizer ai-file-organizer-gui
    echo "Created: ai-file-organizer-macos.tar.gz"
else
    # Linux
    tar czf ai-file-organizer-linux.tar.gz ai-file-organizer ai-file-organizer-gui
    echo "Created: ai-file-organizer-linux.tar.gz"
fi
cd ..

echo "Build complete!"
