#!/bin/bash

# Script to set up this repo as your own GitHub repository
# Usage: ./setup-new-github-repo.sh <github-username> <repo-name>

if [ $# -lt 2 ]; then
    echo "Usage: $0 <github-username> <repo-name>"
    echo "Example: $0 rolki All-jellyfin-media-server"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME=$2

echo "🚀 Setting up repository as your own..."
echo "   GitHub Username: $GITHUB_USERNAME"
echo "   Repository Name: $REPO_NAME"
echo ""

# Remove old remote
echo "📡 Removing old remote..."
git remote remove origin 2>/dev/null || echo "   (No old remote to remove)"

# Stage all changes
echo "📝 Staging all changes..."
git add -A

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "   No changes to commit"
else
    echo "   Changes staged, ready to commit"
    echo ""
    echo "⚠️  You have staged changes. Would you like to commit them now? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "💾 Committing changes..."
        git commit -m "Initial commit: Personal media server setup"
    fi
fi

# Add new remote
echo ""
echo "🔗 Adding new GitHub remote..."
git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo ""
echo "✅ Repository configured!"
echo ""
echo "📋 Next steps:"
echo "   1. Create a new repository on GitHub:"
echo "      - Go to https://github.com/new"
echo "      - Repository name: $REPO_NAME"
echo "      - Choose Public or Private"
echo "      - DO NOT initialize with README, .gitignore, or license"
echo ""
echo "   2. Once created, run:"
echo "      git push -u origin Main"
echo ""
echo "   Or if your default branch is 'main':"
echo "      git branch -M main"
echo "      git push -u origin main"
