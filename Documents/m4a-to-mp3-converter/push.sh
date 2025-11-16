#!/bin/bash

cd "/c/Users/SURYA/Documents/M4A-to-MP3-convertor" || { 
    echo "❌ Project path not found!"; 
    read; exit 1; 
}

if [ -f ".git/index.lock" ]; then
    echo "⚠️ Removing leftover Git lock file..."
    rm -f .git/index.lock
fi

COMMIT_MSG=${1:-"🎧 Update M4A to MP3 Converter Project"}

echo "📦 Adding files..."
git add -A

echo "📝 Committing..."
git commit -m "$COMMIT_MSG" || echo "⚠️ Nothing to commit."

echo "🔗 Setting remote URL..."
git remote set-url origin https://github.com/vsurya2011/M4A-to-MP3-convertor.git

echo "🚀 Pushing to GitHub..."
git push origin main

echo "🎉 Done — Repo Updated!"
read -p "🎯 Press Enter to close..."
