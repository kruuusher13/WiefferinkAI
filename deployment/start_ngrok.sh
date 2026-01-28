#!/bin/bash
echo "Starting ngrok on port 8080..."
echo "Make sure you have ngrok installed: brew install ngrok/ngrok/ngrok"
echo "------------------------------------------------------------------"
echo "Your Public URL will appear below. format: https://<id>.ngrok-free.app"
echo "You must use this domain in your Twilio TwiML Bin (wss://<id>.ngrok-free.app/ws/twilio)"
echo "------------------------------------------------------------------"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok could not be found. Please install it."
    exit 1
fi

ngrok http 8080
