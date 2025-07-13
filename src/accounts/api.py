import logging
import secrets
from datetime import datetime, timedelta

import httpx
from django.conf import settings
from django.shortcuts import redirect
from ninja_extra import api_controller, route
from ninja_jwt.authentication import AsyncJWTAuth

from .models import OAuthState, Repository, Branch
from .schemas import *
from .services.github_service import GitHubService

logger = logging.getLogger(__name__)
github_service = GitHubService()


@api_controller("/auth/github", tags=["GitHub Auth"], auth=None)
class GitHubAuthController:
    @route.get(
        "/login", response={302: None, 400: ErrorResponse}, url_name="github_login"
    )
    async def login(self, request):
        """Initiate GitHub OAuth flow"""
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_REDIRECT_URI:
            return 400, {"detail": "GitHub OAuth not configured", "code": 400}

        scope = "repo,user"
        state = secrets.token_urlsafe(32)

        await OAuthState.objects.acreate(
            state=state, expires_at=datetime.now() + timedelta(minutes=10)
        )

        auth_url = (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={settings.GITHUB_CLIENT_ID}&"
            f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
            f"scope={scope}&state={state}"
        )
        return redirect(auth_url)

    @route.get(
        "/callback",
        response={
            200: dict,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
        },
    )
    async def callback(self, request):
        """GitHub OAuth callback handler"""
        try:
            state = request.GET.get("state")
            if (
                not state
                or not await OAuthState.objects.filter(
                    state=state, expires_at__gt=datetime.now()
                ).aexists()
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

            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data=token_data,
                    timeout=10,
                )
                token_response.raise_for_status()
                token_json = token_response.json()

            access_token = token_json.get("access_token")
            if not access_token:
                return 400, {"detail": "Failed to obtain access token", "code": 400}

            # Get user data and all repositories
            user_data = await github_service.get_user_data(access_token)
            repos = await github_service.get_all_repos(access_token)

            # Create/update user and all related data
            user = await github_service.update_user_data(user_data, access_token)
            for repo in repos:
                repo_obj = await github_service.update_repository(user, repo)
                await github_service.update_branches(access_token, repo_obj)
                await github_service._update_permissions(
                    repo_obj, repo.get("permissions", {})
                )
                await github_service._update_license(repo_obj, repo.get("license"))
                await github_service._update_topics(
                    access_token, repo_obj, repo["name"]
                )

            # Clean up
            await OAuthState.objects.filter(state=state).adelete()

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

    @route.get("/repositories/{user_id}", response=List[RepositorySchema])
    async def list_repositories(self, request, user_id):
        """List all repositories for the authenticated user"""
        repos = []
        async for repo in Repository.objects.filter(user_id=user_id).prefetch_related(
            "branches"
        ):
            branches = []
            async for branch in repo.branches.all():
                branches.append(
                    {
                        "name": branch.name,
                        "protected": branch.protected,
                        "last_commit_sha": branch.last_commit_sha,
                        "last_commit_url": branch.last_commit_url,
                    }
                )

            repos.append(
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
                    "branches": branches,
                }
            )

        return repos

    @route.get(
        "/repositories/{int:repo_id}/branches",
        response=List[BranchSchema],
        auth=AsyncJWTAuth(),
    )
    async def get_repo_branches(self, request, repo_id: int):
        """Get branches for a specific repository"""
        repo = await Repository.objects.aget(repo_id=repo_id, user=request.user)
        branches = []
        async for branch in repo.branches.all():
            branches.append(
                {
                    "name": branch.name,
                    "protected": branch.protected,
                    "last_commit_sha": branch.last_commit_sha,
                    "last_commit_url": branch.last_commit_url,
                }
            )
        return branches

    @route.get(
        "/repositories/{int:repo_id}/branches/{str:branch_name}",
        response=BranchSchema,
        auth=AsyncJWTAuth(),
    )
    async def get_branch(self, request, repo_id: int, branch_name: str):
        """Get details for a specific branch"""
        branch = await Branch.objects.aget(
            repository__repo_id=repo_id, repository__user=request.user, name=branch_name
        )
        return {
            "name": branch.name,
            "protected": branch.protected,
            "last_commit_sha": branch.last_commit_sha,
            "last_commit_url": branch.last_commit_url,
        }
