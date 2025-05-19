#!/bin/bash

# .env file checks
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with your Spotify credentials."
    echo "See the setup instructions for details."
    exit 1
fi

# python packages
REQUIRED_PACKAGES=("flask" "requests" "flask_cors" "python-dotenv" "fuzzywuzzy" "python-Levenshtein")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! pip show "$package" &> /dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

# install missing packages
if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "Installing missing Python packages: ${MISSING_PACKAGES[*]}"
    pip install "${MISSING_PACKAGES[@]}"
fi

# starting the server
cd backend
python3 app.py
