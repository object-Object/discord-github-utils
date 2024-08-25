from dataclasses import dataclass
from typing import Awaitable

from githubkit import Response


@dataclass
class Repository:
    owner: str
    repo: str

    @classmethod
    def parse(cls, value: str):
        if "/" in value:
            owner, repo = value.split("/")
            if owner and repo:
                return cls(owner=owner, repo=repo)

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"


async def gh_request[T](future: Awaitable[Response[T]]) -> T:
    """Helper function to simplify extracting the parsed data from GitHub requests."""
    resp = await future
    return resp.parsed_data
