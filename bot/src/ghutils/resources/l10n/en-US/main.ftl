# command descriptions: command-description_{command}
#   |--------------------------------------------------------------------------------------------------|

# parameter descriptions: parameter-description_{command}_{parameter}
#   |--------------------------------------------------------------------------------------------------|

# common parameters

parameter-description_common_visibility =
    Whether the message should be visible to everyone, or just you.

# /gh issue

command-description_gh-issue =
    Get a link to a GitHub issue.

parameter-description_gh-issue_reference =
    Issue to look up (`owner/repo#123` or `#123`). Use `/gh login` to get autocomplete.

# /gh pr

command-description_gh-pr =
    Get a link to a GitHub pull request.

parameter-description_gh-pr_reference =
    Pull request to look up (`owner/repo#123` or `#123`). Use `/gh login` to get autocomplete.

# /gh commit

command-description_gh-commit =
    Get a link to a GitHub commit.

parameter-description_gh-commit_reference =
    Commit SHA to look up (`owner/repo@sha` or `@sha`). Use `/gh login` to get autocomplete.

# /gh repo

command-description_gh-repo =
    Get a link to a GitHub repository.

# /gh user

command-description_gh-user =
    Get a link to a GitHub user.

# /gh login

command-description_gh-login =
    Authorize GitHub Utils to make requests on behalf of your GitHub account.

# /gh logout

command-description_gh-logout =
    Remove your GitHub account from GitHub Utils.

# /gh status

command-description_gh-status =
    Show information about GitHub Utils.

# /gh search

command-description_gh-search =
    Search for things on GitHub.

# /gh search files

command-description_gh-search-files =
    Search for files in a repository by name.

parameter-description_gh-search-files_repo =
    Repository to search in (`owner/repo`).

parameter-description_gh-search-files_query =
    Filename to search for.

parameter-description_gh-search-files_ref =
    Branch name, tag name, or commit to search in. Defaults to the default branch of the repo.

parameter-description_gh-search-files_exact =
    If true, use exact search; otherwise use fuzzy search.

parameter-description_gh-search-files_limit =
    Maximum number of results to show.
