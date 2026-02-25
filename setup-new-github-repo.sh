#!/usr/bin/env bash

set -euo pipefail

# Script to set up this repo as your own GitHub repository
# Usage: ./setup-new-github-repo.sh <github-username> <repo-name>

usage() {
    echo "Usage: $0 <github-username> <repo-name>"
    echo "Example: $0 rolki All-jellyfin-media-server"
}

if [[ $# -ne 2 ]]; then
    usage
    exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: This script must be run inside a git repository."
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME=$2
NEW_REMOTE_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

echo "Setting up repository as your own..."
echo "  GitHub Username: ${GITHUB_USERNAME}"
echo "  Repository Name: ${REPO_NAME}"
echo "  Current branch: ${CURRENT_BRANCH}"
echo ""

# Remove old remote if it exists
if git remote get-url origin >/dev/null 2>&1; then
    echo "Removing old remote origin..."
    git remote remove origin
else
    echo "No existing origin remote found."
fi

# Stage and optionally commit any local changes
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Staging local changes..."
    git add -A

    if git diff --staged --quiet; then
        echo "No staged changes to commit."
    else
        echo "Staged changes are ready to commit."
        read -r -p "Commit now with default message? [y/N]: " response
        if [[ "${response}" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            echo "Creating commit..."
            git commit -m "Initial commit: Personal media server setup"
        else
            echo "Skipping commit. Changes remain staged."
        fi
    fi
else
    echo "Working tree is clean."
fi

echo ""
echo "Adding new GitHub remote..."
git remote add origin "${NEW_REMOTE_URL}"

echo ""
echo "Repository configured."
echo ""
echo "Next steps:"
echo "  1. Create a new repository on GitHub:"
echo "     - Go to https://github.com/new"
echo "     - Repository name: ${REPO_NAME}"
echo "     - Choose Public or Private"
echo "     - DO NOT initialize with README, .gitignore, or license"
echo ""
echo "  2. Push your current branch:"
echo "     git push -u origin ${CURRENT_BRANCH}"
echo ""
echo "  Optional: rename branch to 'main' before pushing:"
echo "     git branch -M main"
echo "     git push -u origin main"
