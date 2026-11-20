"""Step titles, areas and the operations that are not steps, with the reason for each.

A title is a real action, verb first, unique among all steps (the everyday ones
included). The documentation's own ``definition`` is kept in the registry; titles here
fix its copy-paste slips (``PUT /label/{id}`` is defined as "Create Label" but updates
one, its explanation says so).
"""

from __future__ import annotations

TITLES: dict[tuple[str, str], str] = {
    # Forms and questions
    ("GET", "/user/forms"): "Get forms",
    ("GET", "/form/{id}"): "Get form",
    ("GET", "/form/{id}/questions"): "Get form questions",
    ("GET", "/form/{id}/question/{qid}"): "Get form question",
    ("GET", "/form/{id}/properties"): "Get form properties",
    ("GET", "/form/{id}/properties/{key}"): "Get form property",
    ("GET", "/form/{id}/files"): "Get form uploads",
    ("POST", "/user/forms"): "Create form in account",
    ("POST", "/form"): "Create form",
    ("PUT", "/user/forms"): "Create forms in account from JSON",
    ("PUT", "/form"): "Create forms from JSON",
    ("POST", "/form/{id}/clone"): "Clone form",
    ("POST", "/form/{id}/questions"): "Add question to form",
    ("PUT", "/form/{id}/questions"): "Add questions to form",
    ("POST", "/form/{id}/question/{qid}"): "Edit form question",
    ("POST", "/form/{id}/properties"): "Edit form properties",
    ("PUT", "/form/{id}/properties"): "Edit form properties from JSON",
    ("DELETE", "/form/{id}/question/{qid}"): "Delete form question",
    ("DELETE", "/form/{id}"): "Delete form",
    # Submissions and webhooks
    ("GET", "/form/{id}/submissions"): "Get form submissions",
    ("GET", "/user/submissions"): "Get submissions of all forms",
    ("GET", "/submission/{id}"): "Get submission",
    ("GET", "/form/{id}/webhooks"): "Get form webhooks",
    ("POST", "/form/{id}/submissions"): "Add submission to form",
    ("PUT", "/form/{id}/submissions"): "Add submissions to form",
    ("POST", "/submission/{id}"): "Edit submission",
    ("POST", "/form/{id}/webhooks"): "Add form webhook",
    ("DELETE", "/submission/{id}"): "Delete submission",
    ("DELETE", "/form/{id}/webhooks/{whid}"): "Delete form webhook",
    # Reports, labels and folders
    ("GET", "/form/{id}/reports"): "Get form reports",
    ("GET", "/user/reports"): "Get reports",
    ("GET", "/report/{id}"): "Get report",
    ("GET", "/label/{id}"): "Get label",
    ("GET", "/label/{id}/resources"): "Get label resources",
    ("GET", "/user/folders"): "Get folders",
    ("GET", "/folder/{id}"): "Get folder",
    ("POST", "/form/{id}/reports"): "Create form report",
    ("POST", "/label"): "Create label",
    ("PUT", "/label/{id}"): "Update label",
    ("PUT", "/label/{id}/add-resources"): "Add resources to label",
    ("PUT", "/label/{id}/remove-resources"): "Remove resources from label",
    ("PUT", "/folder/{id}"): "Update folder",
    ("DELETE", "/report/{id}"): "Delete report",
    ("DELETE", "/label/{id}"): "Delete label",
    ("DELETE", "/folder/{id}"): "Delete folder",
    # Account
    ("GET", "/user"): "Get account",
    ("GET", "/user/usage"): "Get monthly usage",
    ("GET", "/user/subusers"): "Get sub-user accounts",
    ("GET", "/user/settings"): "Get account settings",
    ("GET", "/user/history"): "Get account history",
    ("GET", "/system/plan/{planName}"): "Get plan details",
    ("POST", "/user/settings"): "Update account settings",
}

#: Documented operations that are not steps: (method, path) -> the reason, with the
#: documentation's own words.
EXCLUDED: dict[tuple[str, str], str] = {
    ("POST", "/user/login"): (
        "Signing in: it takes the account's username and password and answers with the "
        'account\'s appKey ("Login user with given credentials"). A connection holds an '
        "API key instead, so the step would only ask for a password."
    ),
    ("GET", "/user/logout"): (
        'Signing out ("Logout user", no parameters): it ends a signed-in session and '
        "changes state although it is a GET. Calls with an API key have no session."
    ),
    ("GET", "/user/labels"): (
        "Contradicting facts: its one parameter addResources is required and of kind url "
        "with replace {addResources}, but the path /user/labels has no {addResources}, so "
        "the documentation's client cannot place it (it drops it), while the parameter is "
        "described as including related resources."
    ),
    ("POST", "/folder"): (
        "Contradicting facts: its parameters name (required), parent and color are of kind "
        "url, but the path /folder has none of their tokens, so the documentation's client "
        "would send none of them; the curl example sends them as form fields (-d "
        '"name=…"). The folder endpoints are deprecated in favour of labels.'
    ),
}

AREAS: dict[str, tuple[str, ...]] = {
    "Forms and questions": ("/user/forms", "/form"),
    "Submissions and webhooks": ("/user/submissions", "/submission", "submissions", "webhooks"),
    "Reports, labels and folders": ("/report", "/label", "/folder", "/user/folders", "reports"),
    "Account": ("/user", "/system"),
}


def area_of(path: str) -> str:
    """The area of a documented path: the first whose marker the path ends with or
    starts with, most specific first."""
    tail = path.rstrip("/").rsplit("/", 1)[-1]
    if tail.startswith("{"):
        tail = path.rstrip("/").rsplit("/", 2)[-2]
    for area in ("Submissions and webhooks", "Reports, labels and folders"):
        for marker in AREAS[area]:
            if marker.startswith("/"):
                if path == marker or path.startswith(marker + "/"):
                    return area
            elif tail == marker:
                return area
    if path == "/user/forms" or path == "/form" or path.startswith("/form/"):
        return "Forms and questions"
    return "Account"


#: The verbs a title may start with.
VERBS = frozenset(
    {
        "Get",
        "List",
        "Describe",
        "Create",
        "Add",
        "Edit",
        "Update",
        "Clone",
        "Remove",
        "Delete",
        "Download",
        "Test",
        "Check",
        "Build",
    }
)
