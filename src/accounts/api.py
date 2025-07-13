from ninja_extra import api_controller, http_get
from ninja import Schema
from django.shortcuts import redirect
from django.conf import settings
from django.db import transaction
import requests
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
import logging
import secrets
from .models import *
from typing import List, Optional, Dict, Any
from ninja.security import HttpBearer

logger = logging.getLogger(__name__)

# Encryption setup for access tokens
fernet = Fernet(settings.FERNET_KEY)


class ErrorResponse(Schema):
    detail: str
    code: int


class GitHubUser(Schema):
    login: str
    id: int
    avatar_url: Optional[str]
    bio: Optional[str]
    public_repos: int
    followers: int
    following: int


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            decrypted_token = fernet.decrypt(token.encode()).decode()
            user = User.objects.get(access_token=token)
            if user.sso_token_expiry < datetime.now():
                return None
            return user
        except Exception:
            return None


@api_controller("/github", tags=["GitHub"], auth=None)
class GitHubAuthController:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}

    def encrypt_token(self, token: str) -> str:
        return fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        return fernet.decrypt(encrypted_token.encode()).decode()

    def _make_github_request(
        self, access_token: str, url: str, params: dict = None, headers: dict = None
    ) -> Dict[str, Any]:
        """Helper method to make GitHub API requests"""
        if headers is None:
            headers = {**self.headers, "Authorization": f"Bearer {access_token}"}
        else:
            headers = {**headers, "Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    @http_get(
        "/login", response={302: None, 400: ErrorResponse}, url_name="github_login"
    )
    def login(self, request):
        """
        Initiate GitHub OAuth flow.
        Requires GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI in settings.
        """
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_REDIRECT_URI:
            return 400, {"detail": "GitHub OAuth not configured", "code": 400}

        scope = "repo,user"
        # Generate a secure random state token
        state = secrets.token_urlsafe(32)

        # Store state in database with expiration
        OAuthState.objects.create(
            state=state, expires_at=datetime.now() + timedelta(minutes=10)
        )

        auth_url = (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={settings.GITHUB_CLIENT_ID}&"
            f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
            f"scope={scope}&state={state}"
        )
        return redirect(auth_url)

    @http_get(
        "/callback",
        response={
            200: GitHubUser,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
        },
    )
    def callback(self, request):
        """GitHub OAuth callback handler"""
        try:
            # Validate state and get code
            state = request.GET.get("state")
            if (
                not state
                or not OAuthState.objects.filter(
                    state=state, expires_at__gt=datetime.now()
                ).exists()
            ):
                return 401, {"detail": "Invalid state parameter", "code": 401}

            code = request.GET.get("code")
            if not code:
                return 400, {"detail": "Authorization code missing", "code": 400}

            # Exchange code for access token
            token_data = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            }

            token_response = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data=token_data,
                timeout=10,
            )
            token_response.raise_for_status()

            access_token = token_response.json().get("access_token")
            if not access_token:
                return 400, {"detail": "Failed to obtain access token", "code": 400}

            # Get user data and all repositories
            user_data = self._make_github_request(
                access_token, "https://api.github.com/user"
            )
            repos = self._get_all_repos(access_token)

            # Create/update user and all related data
            user = self._update_user_data(user_data, access_token)
            for repo in repos:
                repo_obj = self._update_repository(user, repo)
                self._update_branches(access_token, repo_obj)
                self._update_permissions(repo_obj, repo.get("permissions", {}))
                self._update_license(repo_obj, repo.get("license"))
                self._update_topics(access_token, repo_obj, repo["name"])

            # Clean up and return response
            OAuthState.objects.filter(state=state).delete()

            return 200, {
                "login": user.github_login,
                "id": user.github_id,
                "avatar_url": user.avatar,
                "bio": user.bio,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
                "access_token": self.encrypt_token(access_token),
                "token_expiry": (datetime.now() + timedelta(days=7)).isoformat(),
            }

        except requests.HTTPError as e:
            logger.error(f"GitHub API error: {str(e)}")
            return e.response.status_code, {
                "detail": "GitHub API request failed",
                "code": e.response.status_code,
            }
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}", exc_info=True)
            return 500, {"detail": "Authentication failed", "code": 500}

    def _get_all_repos(self, access_token: str) -> List[dict]:
        """Fetch all repositories with pagination"""
        repos = []
        page = 1
        per_page = 100

        while True:
            try:
                response = requests.get(
                    "https://api.github.com/user/repos",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"page": page, "per_page": per_page, "sort": "updated"},
                    timeout=10,
                )
                response.raise_for_status()

                batch = response.json()
                if not batch:
                    break

                repos.extend(batch)
                page += 1

                # Stop if we've got all repos (GitHub's max page size is 100)
                if len(batch) < per_page:
                    break

            except requests.HTTPError as e:
                logger.error(f"Failed to fetch repos page {page}: {str(e)}")
                break

        return repos

    @transaction.atomic
    def _update_user_data(self, user_data: dict, access_token: str) -> User:
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
    def _update_repository(self, user: User, repo_data: dict) -> Repository:
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
                "fork": repo_data["fork"],
                "url": repo_data["url"],
                "html_url": repo_data["html_url"],
                "git_url": repo_data["git_url"],
                "ssh_url": repo_data["ssh_url"],
                "clone_url": repo_data["clone_url"],
                "svn_url": repo_data["svn_url"],
                "homepage": repo_data.get("homepage"),
                "size": repo_data["size"],
                "stargazers_count": repo_data["stargazers_count"],
                "watchers_count": repo_data["watchers_count"],
                "language": repo_data.get("language"),
                "has_issues": repo_data["has_issues"],
                "has_projects": repo_data["has_projects"],
                "has_wiki": repo_data["has_wiki"],
                "has_pages": repo_data["has_pages"],
                "forks_count": repo_data["forks_count"],
                "open_issues_count": repo_data["open_issues_count"],
                "archived": repo_data["archived"],
                "disabled": repo_data["disabled"],
                "visibility": repo_data["visibility"],
                "pushed_at": repo_data["pushed_at"],
                "created_at": repo_data["created_at"],
                "updated_at": repo_data["updated_at"],
            },
        )
        return repo

    @transaction.atomic
    def _update_branches(self, access_token: str, repository: Repository):
        """Update branches for a repository"""
        try:
            branches = self._make_github_request(
                access_token,
                f"https://api.github.com/repos/{repository.full_name}/branches",
            )

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
            logger.error(
                f"Failed to update branches for {repository.full_name}: {str(e)}"
            )

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

    @http_get(
        "/user", auth=AuthBearer(), response={200: GitHubUser, 401: ErrorResponse}
    )
    def get_current_user(self, request):
        """Get current authenticated user"""
        user = request.auth
        return 200, {
            "login": user.github_login,
            "id": user.github_id,
            "avatar_url": user.avatar,
            "bio": user.bio,
            "public_repos": user.public_repos,
            "followers": user.followers,
            "following": user.following,
        }
