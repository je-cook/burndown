import math

import pandas as pd
import requests


class Query:
    start: str = """
    query($owner: String!, $name: String!,"""
    start_issue: str = " $cursorIssues: String"
    start_pr: str = "$cursorPRs: String"
    mid: str = """) {
      repository(owner: $owner, name: $name) {
    """
    end: str = """
      }
    }
    """
    issue: str = """
        issues(first: 100, after: $cursorIssues, states: [OPEN, CLOSED]) {
          edges {
            node {
              number
              title
              createdAt
              closedAt
              labels(first: 10) {
                nodes {
                  name
                }
              }
              comments(first: 10) {
                nodes {
                  body
                  createdAt
                }
              }
            }
            cursor
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }"""
    pr: str = """
        pullRequests(first: 100, after: $cursorPRs, states: [OPEN, CLOSED]) {
          edges {
            node {
              number
              title
              createdAt
              closedAt
              labels(first: 10) {
                nodes {
                  name
                }
              }
            }
            cursor
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }"""
    just_issue_start: str = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {"""
    issue_no: str = "issue{}: issue(number: {})"
    just_issue_end: str = """{
          number
          createdAt
          comments(first: 100) {
            nodes {
              createdAt
            }
          }
        }
    """

    def __init__(self, orgrepo: str, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.owner, self.name = orgrepo.split("/")

    @property
    def get_pr_and_issue(self) -> str:
        return (
            self.start
            + f"{self.start_issue}, {self.start_pr}{self.mid}"
            + self.issue
            + self.pr
            + self.end
        )

    @property
    def get_issue(self):
        return self.start + f"{self.start_issue}{self.mid}" + self.issue + self.end

    @property
    def get_pr(self):
        return self.start + f"{self.start_pr}{self.mid}" + self.pr + self.end

    def get_query(self, has_issue, has_pr):
        if has_pr and has_issue:
            query = self.get_pr_and_issue
        elif has_issue:
            query = self.get_issue
        elif has_pr:
            query = self.get_pr
        else:
            query = False
        return query


def extra_processing(issues, to_process_issues, query: Query) -> None:
    further_process = []
    for issue_no, (ind, issue) in to_process_issues.items():
        labels = [label["name"] for label in issue["labels"]["nodes"]]
        is_mr = (
            "gitlab merge request" in labels
            and (issue.get("closedAt") or "").startswith("2023-07-07")
            and issue["title"].endswith(("[merged]", "[closed]"))
        )

        if is_mr:
            issues[ind]["is_pr"] = True
            for comment in issue["comments"]["nodes"]:
                if "merged" in comment["body"] or "closed" in comment["body"]:
                    issues[ind]["closed_at"] = comment["createdAt"]
                    break
            else:
                further_process.append(issue_no)

        elif (issue.get("closedAt") or "").startswith("2023-07-07"):
            further_process.append(issue_no)

    loops = math.ceil(len(further_process) / 100)
    for loop in range(loops):
        qry = query.just_issue_start
        for isu in further_process[loop * 100 : (loop + 1) * 100]:
            qry += query.issue_no.format(isu, isu)
            qry += query.just_issue_end
        qry += query.end
        variables = {
            "owner": query.owner,
            "name": query.name,
        }
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": qry, "variables": variables},
            headers=query.headers,
        )
        data = response.json()
        if data.get("errors"):
            print(data.get("errors"))
        else:
            for ind, issue in data["data"]["repository"].items():
                created_at = (
                    issue["createdAt"]
                    if len(issue["comments"]["nodes"]) == 0
                    else issue["comments"]["nodes"][-1]["createdAt"]
                )
                issues[to_process_issues[issue["number"]][0]]["closed_at"] = created_at


def extra_processing_check(query, issue, issues, to_process) -> None:
    if query.name == "process" and (issue.get("closedAt") or "").startswith(
        "2023-07-07",
    ):
        to_process[issue["number"]] = (len(issues), issue)


def fetch_github_data(orgrepo: str, token: str, *, debug: bool) -> pd.DataFrame:
    issues = []

    q_setup = Query(orgrepo, token)

    cursor_issues = cursor_prs = None
    has_next_page_issues = has_next_page_prs = True
    page_count = 0
    to_process = {}
    while (query := q_setup.get_query(has_next_page_issues, has_next_page_prs)) and (
        (debug and page_count < 3) or not debug
    ):
        variables = {
            "owner": q_setup.owner,
            "name": q_setup.name,
            "cursorIssues": cursor_issues,
            "cursorPRs": cursor_prs,
        }
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=q_setup.headers,
        )
        data = response.json()

        if data.get("errors"):
            print(data.get("errors"))
            has_next_page_prs = has_next_page_issues = False
            continue

        if has_next_page_issues:
            for edge in data["data"]["repository"]["issues"]["edges"]:
                issue = edge["node"]
                extra_processing_check(q_setup, issue, issues, to_process)
                issues.append({
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue["createdAt"],
                    "closed_at": issue.get("closedAt", None),
                    "is_pr": False,
                })
            # Check if there are more pages
            page_info_is = data["data"]["repository"]["issues"]["pageInfo"]
            has_next_page_issues = page_info_is["hasNextPage"]
            cursor_issues = page_info_is["endCursor"]

        if has_next_page_prs:
            for edge in data["data"]["repository"]["pullRequests"]["edges"]:
                issue = edge["node"]
                issues.append({
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue["createdAt"],
                    "closed_at": issue["closedAt"],
                    "is_pr": True,
                })

            # Check if there are more pages
            page_info_pr = data["data"]["repository"]["pullRequests"]["pageInfo"]
            has_next_page_prs = page_info_pr["hasNextPage"]
            cursor_prs = page_info_pr["endCursor"]

        page_count += 1

    if to_process != {}:
        extra_processing(issues, to_process, q_setup)

    return pd.DataFrame(issues)
