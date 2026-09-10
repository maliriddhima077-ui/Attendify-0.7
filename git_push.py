"""
Attendify — GitHub Remote Upload Helper
This script allows you to push the Attendify repository to any GitHub repository.
Usage:
    python git_push.py https://github.com/<your-username>/<your-repo-name>.git
"""
import sys
import os
from dulwich import porcelain
from dulwich.repo import Repo

REPO_PATH = os.path.dirname(os.path.abspath(__file__))


def push_to_github(remote_url):
    print(f"Connecting to remote repository: {remote_url}")
    repo = Repo(REPO_PATH)
    
    # Configure remote origin
    try:
        porcelain.remote_add(repo, b'origin', remote_url.encode('utf-8'))
        print("Configured remote 'origin'.")
    except Exception:
        # Remote origin might already exist, update it
        config = repo.get_config()
        config.set((b'remote', b'origin'), b'url', remote_url.encode('utf-8'))
        config.write_to_path()
        print("Updated remote 'origin' URL.")

    # Push to origin main/master
    try:
        print("Pushing commits to GitHub...")
        porcelain.push(repo, remote_location=b'origin', refspecs=[b'refs/heads/master:refs/heads/main'])
        print("Successfully uploaded Attendify to GitHub!")
    except Exception as e:
        print(f"Push error: {e}")
        print("\nIf you are asked for authentication:")
        print("1. Create a GitHub Personal Access Token at https://github.com/settings/tokens")
        print("2. Use the remote URL format: https://<TOKEN>@github.com/<USERNAME>/<REPO>.git")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        push_to_github(sys.argv[1])
    else:
        print("Please provide your GitHub repository URL.")
        print("Example:")
        print("    python git_push.py https://github.com/your-username/attendify.git")
