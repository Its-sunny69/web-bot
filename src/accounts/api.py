from ninja_extra import api_controller, http_get
from django.shortcuts import redirect
import os
# import httpx

@api_controller("/github", tags=["GitHub"])
class GitHubController:
    @http_get("/login")
    def login(self, request):
        client_id = os.getenv("GITHUB_CLIENT_ID")
        redirect_uri = os.getenv("GITHUB_REDIRECT_URI")
        return redirect(
            f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=repo"
        )

    @http_get("/callback")
    def callback(self, request):
        code = request.GET.get("code")
        token_url = "https://github.com/login/oauth/access_token"
        # res = httpx.post(token_url, headers={"Accept": "application/json"}, data={
        #     "client_id": os.getenv("GITHUB_CLIENT_ID"),
        #     "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        #     "code": code,
        # })
        # access_token = res.json().get("access_token")
        # return {"token": access_token}
