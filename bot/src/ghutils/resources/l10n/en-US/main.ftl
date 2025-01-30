# command descriptions: {command}_description
#   |--------------------------------------------------------------------------------------------------|

# parameter descriptions: {command}_parameter-description_{parameter}
#   |--------------------------------------------------------------------------------------------------|

# common parameters

-parameter-description_visibility =
    Whether the message should be visible to everyone, or just you.

# /gh issue

gh-issue_description =
    Get a link to a GitHub issue.

gh-issue_parameter-description_reference =
    Issue to look up (`owner/repo#123` or `#123`). Use `/gh login` to get autocomplete.

gh-issue_parameter-description_visibility =
    {-parameter-description_visibility}

# /gh pr

gh-pr_description =
    Get a link to a GitHub pull request.

gh-pr_parameter-description_reference =
    Pull request to look up (`owner/repo#123` or `#123`). Use `/gh login` to get autocomplete.

gh-pr_parameter-description_visibility =
    {-parameter-description_visibility}

# /gh commit

gh-commit_description =
    Get a link to a GitHub commit.

gh-commit_parameter-description_reference =
    Commit SHA to look up (`owner/repo@sha` or `@sha`). Use `/gh login` to get autocomplete.

gh-commit_parameter-description_visibility =
    {-parameter-description_visibility}

# /gh repo

gh-repo_description =
    Get a link to a GitHub repository.

gh-repo_parameter-description_repo =
    Repository to look up (`owner/repo`). Use `/gh login` to get autocomplete.

gh-repo_parameter-description_visibility =
    {-parameter-description_visibility}

# /gh user

gh-user_description =
    Get a link to a GitHub user.

gh-user_parameter-description_user =
    Username to look up. Use `/gh login` to get autocomplete.

gh-user_parameter-description_visibility =
    {-parameter-description_visibility}

# /gh login

gh-login_description =
    Authorize GitHub Utils to make requests on behalf of your GitHub account.

# /gh logout

gh-logout_description =
    Remove your GitHub account from GitHub Utils.

# /gh status

gh-status_description =
    Show information about GitHub Utils.

gh-status_parameter-description_visibility =
    {-parameter-description_visibility}

gh-status_text_title =
    Bot Status

gh-status_text_commit =
    Deployed commit

gh-status_text_commit_unknown =
    Unknown

gh-status_text_deployment-time =
    Deployment time

gh-status_text_deployment-time_unknown =
    Unknown

gh-status_text_uptime =
    Uptime

gh-status_text_installs =
    Install count

gh-status_text_installs_value =
    { $servers ->
        [one] 1 server
        *[other] { $servers } servers
    }
    { $users ->
        [one] 1 individual user
        *[other] { $users } individual users
    }

gh-status_text_commands =
    Commands

# /gh search

gh-search_description =
    Search for things on GitHub.

# /gh search files

gh-search-files_description =
    Search for files in a repository by name.

gh-search-files_parameter-description_repo =
    Repository to search in (`owner/repo`).

gh-search-files_parameter-description_query =
    Filename to search for.

gh-search-files_parameter-description_ref =
    Branch name, tag name, or commit to search in. Defaults to the default branch of the repo.

gh-search-files_parameter-description_exact =
    If true, use exact search; otherwise use fuzzy search.

gh-search-files_parameter-description_limit =
    Maximum number of results to show.

gh-search-files_parameter-description_visibility =
    {-parameter-description_visibility}
