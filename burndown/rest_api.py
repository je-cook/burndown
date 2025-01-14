import pandas as pd
import requests


class Query:
    def __init__(self, orgrepo: str, token: str) -> None:
        self.headers = {"Authorization": f"token {token}"} if token else {}
        self.owner, self.name = orgrepo.split("/")
        self.request = (
            f"https://api.github.com/repos/{orgrepo}/issues?state=all&page={{}}"
        )


def extra_processing(issues, to_process_issues, query):
    further_process = []
    for issue_no, (ind, issue) in to_process_issues.items():
        labels = [l["name"] for l in issue["labels"]]

        is_mr = (
            "gitlab merge request" in labels
            and (issue.get("closed_at", "") or "").startswith("2023-07-07")
            and issue["title"].endswith(("[merged]", "[closed]"))
        )
        if is_mr:
            issues[ind]["is_pr"] = True
            if issue["comments"] > 0:
                response = requests.get(issue["comments_url"], headers=query.headers)
                comments = response.json()
                for comment in comments:
                    if "merged" in comment["body"] or "closed" in comment["body"]:
                        issues[ind]["closed_at"] = comment["created_at"]
                        break
                else:
                    issues[ind]["closed_at"] = comments[-1].get(
                        "created_at", issue.get("closed_at")
                    )

        elif (issue.get("closed_at") or "").startswith("2023-07-07"):
            if issue["comments"] > 0:
                response = requests.get(issue["comments_url"], headers=query.headers)
                comments = response.json()
                issues[ind]["closed_at"] = (
                    comments[-1].get("created_at", issue.get("closed_at"))
                    if comments
                    else issue.get("closed_at")
                )


def extra_processing_check(query, issue, issues, to_process) -> None:
    if query.name == "process" and (issue.get("closed_at") or "").startswith(
        "2023-07-07",
    ):
        to_process[issue["number"]] = (len(issues), issue)


def fetch_github_data(orgrepo, token, *, debug: bool):
    issues = []
    page = 1
    to_process = {}
    query = Query(orgrepo, token)
    while (page < 30) if debug else True:
        response = requests.get(query.request.format(page), headers=query.headers)
        data = response.json()

        if not data:
            break

        for issue in data:
            extra_processing_check(query, issue, issues, to_process)
            issues.append({
                "issue_number": issue["number"],
                "title": issue["title"],
                "created_at": issue["created_at"],
                "closed_at": issue.get("closed_at", None),
                "is_pr": "pull_request" in issue,
            })

        page += 1

    if to_process != {}:
        extra_processing(issues, to_process, query)

    return pd.DataFrame(issues)
