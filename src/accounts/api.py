import logging
import requests
import secrets
from typing import List
from datetime import datetime, timedelta

from django.shortcuts import redirect
from django.conf import settings

from ninja_extra import api_controller, http_get

from .models import *
from .services.github_service import GitHubService
from .schemas import *

github_service = GitHubService()
logger = logging.getLogger(__name__)

@api_controller("/auth/github", tags=["GitHub Auth"], auth=None)
class GitHubAuthController:
    @http_get(
        "/login", response={302: None, 400: ErrorResponse}, url_name="github_login"
    )
    def login(self, request):
        """Initiate GitHub OAuth flow"""
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_REDIRECT_URI:
            return 400, {"detail": "GitHub OAuth not configured", "code": 400}

        scope = "repo,user"
        state = secrets.token_urlsafe(32)

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
            200: dict,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
        },
    )
    def callback(self, request):
        """GitHub OAuth callback handler"""
        try:
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
            user_data = github_service.get_user_data(access_token)
            repos = github_service.get_all_repos(access_token)

            # Create/update user and all related data
            user = github_service.update_user_data(user_data, access_token)
            for repo in repos:
                repo_obj = github_service.update_repository(user, repo)
                github_service.update_branches(access_token, repo_obj)
                github_service._update_permissions(repo_obj, repo.get("permissions", {}))
                github_service._update_license(repo_obj, repo.get("license"))
                github_service._update_topics(access_token, repo_obj, repo["name"])

            # Clean up
            OAuthState.objects.filter(state=state).delete()

            return 200, {
                "login": user.github_login,
                "id": user.github_id,
                "avatar_url": user.avatar,
                "bio": user.bio,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
                "access_token": github_service.encrypt_token(access_token),
                "token_expiry": (datetime.now() + timedelta(days=7)).isoformat(),
            }
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}", exc_info=True)
            return 500, {"detail": "Authentication failed", "code": 500}

    @http_get("/repositories", response=List[RepositorySchema])
    def list_repositories(self, request):
        """List all repositories for the authenticated user"""
        user = request.auth
        repos = Repository.objects.filter(user=user).prefetch_related("branches")
        return [
            {
                "id": repo.repo_id,
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "description": repo.description,
                "html_url": repo.html_url,
                "language": repo.language,
                "stargazers_count": repo.stargazers_count,
                "forks_count": repo.forks_count,
                "open_issues_count": repo.open_issues_count,
                "branches": [
                    {
                        "name": branch.name,
                        "protected": branch.protected,
                        "last_commit_sha": branch.last_commit_sha,
                        "last_commit_url": branch.last_commit_url,
                    }
                    for branch in repo.branches.all()
                ],
            }
            for repo in repos
        ]

    @http_get("/repositories/{int:repo_id}/branches", response=List[BranchSchema])
    def get_repo_branches(self, request, repo_id: int):
        """Get branches for a specific repository"""
        user = request.auth
        repo = Repository.objects.get(repo_id=repo_id, user=user)
        branches = repo.branches.all()
        return [
            {
                "name": branch.name,
                "protected": branch.protected,
                "last_commit_sha": branch.last_commit_sha,
                "last_commit_url": branch.last_commit_url,
            }
            for branch in branches
        ]

    @http_get("/repositories/{int:repo_id}/branches/{str:branch_name}", response=BranchSchema)
    def get_branch(self, request, repo_id: int, branch_name: str):
        """Get details for a specific branch"""
        user = request.auth
        branch = Branch.objects.get(
            repository__repo_id=repo_id, repository__user=user, name=branch_name
        )
        return {
            "name": branch.name,
            "protected": branch.protected,
            "last_commit_sha": branch.last_commit_sha,
            "last_commit_url": branch.last_commit_url,
        }
