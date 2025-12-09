#!/bin/bash

# --- Configuration ---
# Set the directory containing the files you want to push
PROJECT_DIR="C:/Users/SURYA/Documents/yolo safety detection render/Dashboard"

# --- Script Logic ---

# 1. Check if the project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Directory $PROJECT_DIR not found."
    exit 1
fi

# 2. Navigate to the project directory
echo "Navigating to: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 3. Add all changes (including new, modified, and deleted files)
echo "Adding all files..."
git add .

# 4. Prompt the user for a commit message
echo "Enter commit message (e.g., 'Ready for Render deployment'):"
read COMMIT_MESSAGE

# 5. Commit the changes
echo "Committing with message: $COMMIT_MESSAGE"
git commit -m "$COMMIT_MESSAGE"

# 6. Push the changes to the remote repository (assuming 'origin' is your GitHub repo)
echo "Pushing changes to GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Push successful! You can now deploy on Render."
else
    echo "❌ Push failed. Check your network connection and Git credentials."
fi