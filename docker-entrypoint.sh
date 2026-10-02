#!/bin/sh
set -e
cd /app

# external/config.json, if present, replaces the config built into the image
if [ -f external/config.json ]; then
    ln -sf /app/external/config.json /app/config.json
fi

# packages needed by the external plugins
if [ -f external/requirements.txt ]; then
    echo "Installing external packages..."
    pip install -r external/requirements.txt
fi

exec python main.py
