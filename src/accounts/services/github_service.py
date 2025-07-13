import requests
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import logging
from django.conf import settings
from django.db import transaction
from ..models import *
from typing import List , Optional

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.fernet = Fernet(settings.FERNET_KEY)

    def encrypt_token(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        return self.fernet.decrypt(encrypted_token.encode()).decode()

    def _make_request(self, access_token: str, url: str, params: dict = None, headers: dict = None) -> dict:
        """Helper method to make GitHub API requests"""
        if headers is None:
            headers = {**self.headers, "Authorization": f"Bearer {access_token}"}
        else:
            headers = {**headers, "Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_user_data(self, access_token: str) -> dict:
        """Fetch user data from GitHub"""
        return self._make_request(access_token, "https://api.github.com/user")

    def get_all_repos(self, access_token: str) -> List[dict]:
        """Fetch all repositories with pagination"""
        repos = []
        page = 1
        per_page = 100

        while True:
            try:
                batch = self._make_request(
                    access_token,
                    "https://api.github.com/user/repos",
                    params={"page": page, "per_page": per_page, "sort": "updated"}
                )
                if not batch:
                    break

                repos.extend(batch)
                page += 1

                if len(batch) < per_page:
                    break
            except requests.HTTPError as e:
                logger.error(f"Failed to fetch repos page {page}: {str(e)}")
                break

        return repos

    def get_repo_branches(self, access_token: str, full_name: str) -> List[dict]:
        """Fetch branches for a repository"""
        return self._make_request(
            access_token,
            f"https://api.github.com/repos/{full_name}/branches"
        )

    def get_repo_topics(self, access_token: str, full_name: str) -> dict:
        """Fetch repository topics"""
        return self._make_request(
            access_token,
            f"https://api.github.com/repos/{full_name}/topics",
            headers={"Accept": "application/vnd.github.mercy-preview+json"}
        )

    @transaction.atomic
    def update_user_data(self, user_data: dict, access_token: str) -> User:
        """Create or update user from GitHub data"""
        encrypted_token = self.encrypt_token(access_token)

        user, created = User.objects.update_or_create(
            github_id=user_data["id"],
            defaults={
                "github_login": user_data["login"],
                "avatar": user_data.get("avatar_url"),
                "bio": user_data.get("bio"),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "access_token": encrypted_token,
                "sso_token_expiry": datetime.now() + timedelta(days=7),
            },
        )
        return user

    @transaction.atomic
    def update_repository(self, user: User, repo_data: dict) -> Repository:
        """Create or update repository"""
        repo, created = Repository.objects.update_or_create(
            repo_id=repo_data["id"],
            defaults={
                "user": user,
                "node_id": repo_data["node_id"],
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "private": repo_data["private"],
                "description": repo_data.get("description"),
                # ... (keep all other repository fields from your original code)
            },
        )
        return repo

    @transaction.atomic
    def update_branches(self, access_token: str, repository: Repository):
        """Update branches for a repository"""
        try:
            branches = self.get_repo_branches(access_token, repository.full_name)

            # Delete old branches not present anymore
            existing_branches = set(repository.branches.values_list("name", flat=True))
            current_branches = {branch["name"] for branch in branches}
            repository.branches.filter(
                name__in=existing_branches - current_branches
            ).delete()

            # Create or update branches
            for branch in branches:
                commit = branch.get("commit", {})
                Branch.objects.update_or_create(
                    repository=repository,
                    name=branch["name"],
                    defaults={
                        "protected": branch.get("protected", False),
                        "last_commit_sha": commit.get("sha", ""),
                        "last_commit_url": commit.get("url", ""),
                    },
                )
        except Exception as e:
            logger.error(f"Failed to update branches for {repository.full_name}: {str(e)}")

    @transaction.atomic
    def _update_permissions(self, repository: Repository, permissions: dict):
        """Update repository permissions"""
        if permissions:
            RepositoryPermission.objects.update_or_create(
                repository=repository,
                defaults={
                    "admin": permissions.get("admin", False),
                    "maintain": permissions.get("maintain", False),
                    "push": permissions.get("push", False),
                    "triage": permissions.get("triage", False),
                    "pull": permissions.get("pull", True),
                },
            )

    @transaction.atomic
    def _update_license(self, repository: Repository, license_data: Optional[dict]):
        """Update repository license"""
        if license_data:
            License.objects.update_or_create(
                repository=repository,
                defaults={
                    "key": license_data.get("key", ""),
                    "name": license_data.get("name", ""),
                    "spdx_id": license_data.get("spdx_id", ""),
                    "url": license_data.get("url"),
                    "node_id": license_data.get("node_id", ""),
                },
            )

    @transaction.atomic
    def _update_topics(self, access_token: str, repository: Repository, repo_name: str):
        """Update repository topics"""
        try:
            topics_response = self._make_github_request(
                access_token,
                f"https://api.github.com/repos/{repository.full_name}/topics",
                headers={"Accept": "application/vnd.github.mercy-preview+json"},
            )
            topics = topics_response.get("names", [])

            # Clear existing topics
            repository.topics.clear()

            # Add new topics
            for topic_name in topics:
                topic, _ = Topic.objects.get_or_create(name=topic_name)
                repository.topics.add(topic)
        except Exception as e:
            logger.error(f"Failed to update topics for {repo_name}: {str(e)}")

