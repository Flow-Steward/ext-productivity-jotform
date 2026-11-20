"""The everyday steps: their inputs, outputs and descriptions.

They are built on the documented operations (runtime/composites.py, runtime/readiness.py)
and come first in the step list. Contract files are generated from this module by
build_contracts.py.
"""

from __future__ import annotations

from typing import Any

WARNINGS = {
    "name": "warnings",
    "type": "array",
    "items": {"type": "string"},
    "description": "What the step could not do fully or what to check.",
}
LIMIT_LEFT = {
    "name": "limit_left",
    "type": ["integer", "null"],
    "description": "The API calls the key has left today, as Jotform reports it (limit-left).",
}
#: The outputs every write returns about what the answer confirms.
PROCESSING_OUTPUTS: list[dict[str, Any]] = [
    {
        "name": "processing",
        "type": ["string", "null"],
        "enum": ["completed", "accepted", None],
        "description": (
            "completed: Jotform answered that the change is made. accepted: it accepted the "
            "request to carry it out afterwards (no documented operation does). None when "
            "nothing was sent (a test run, or nothing to change)."
        ),
    },
    {
        "name": "applied",
        "type": ["boolean", "null"],
        "description": (
            "True with processing completed. False when nothing was sent. None when Jotform "
            "confirmed a list of records but its answer does not say which (see unanswered)."
        ),
    },
    {
        "name": "check",
        "type": ["object", "null"],
        "additionalProperties": True,
        "description": "With processing accepted: the step that reads the outcome.",
    },
]
#: A batch write: how many of the records sent the answer does not account for.
UNANSWERED_OUTPUT: dict[str, Any] = {
    "name": "unanswered",
    "type": ["integer", "null"],
    "description": (
        "0 when the answer lists the records added. The number of records sent when Jotform "
        "confirmed the request but its answer is not the documented list: check them in "
        "Jotform. None when nothing was sent."
    ),
}


def _text(name: str, title: str, description: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "title": title, "description": description, "type": "string", **extra}


def _int(name: str, title: str, description: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "title": title, "description": description, "type": "integer", **extra}


def _out(name: str, kind: Any, description: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "type": kind, "description": description, **extra}


FORM_ID = _text(
    "form_id",
    "Form ID",
    "The number in the form's address: 30693660548966 for jotform.com/30693660548966.",
    maxLength=30,
)
FILTER_HELP = (
    'Documented filter as an object, for example {"status": "ACTIVE"} or '
    '{"updated_at:gt": "2026-11-01 00:00:00"}; gt, lt and ne compare. Dates as '
    "YYYY-MM-DD HH:MM:SS."
)
PAGING_INPUTS = [
    _int(
        "start_offset",
        "Start at",
        "The offset to start at: 0, or next_offset of an earlier run.",
        minimum=0,
        maximum=10000000,
    ),
    _int(
        "max_records",
        "At most",
        "The most records to read in this step. Default 10000. Only whole pages are "
        "returned, so next_offset never skips a record; the first page is returned whole.",
        minimum=1,
        maximum=100000,
    ),
    _int(
        "page_size",
        "Records per page",
        "Records asked for per page: 1000 (the documented maximum) by default. A page too "
        "large for the output is read again in smaller pages; the next one at this size.",
        minimum=1,
        maximum=1000,
    ),
    _text(
        "output",
        "Return as",
        "step: in the step output (default). file: one JSON workflow file of up to 40 MB, for long lists.",
        enum=["step", "file"],
    ),
]
PAGING_OUTPUTS = [
    _out("count", "integer", "How many records were read."),
    _out("complete", "boolean", "True when every matching record was read."),
    _out(
        "next_offset",
        ["integer", "null"],
        "The offset to start the next run at when not complete.",
    ),
    _out("page_size", "integer", "The records asked for per page."),
]
FILE_OUTPUT = _out(
    "file",
    ["string", "null"],
    "The JSON workflow file, when output is file.",
    value_type="artifact_handle",
)

COMPOSITES: list[dict[str, Any]] = [
    {
        "operation_id": "test_connection",
        "title": "Test connection",
        "kind": "read",
        "calls": ["GET /user"],
        "description": (
            "Checks that Jotform accepts the connection's API key at the connection's region: "
            "reads the account. Returns its username, name, plan and the API calls left today."
        ),
        "inputs": [],
        "outputs": [
            _out("connected", "boolean", "True when Jotform accepted the key."),
            _out("region", "string", "standard, eu or hipaa."),
            _out("username", "string", "The account's username."),
            _out("name", ["string", "null"], "The account's name."),
            _out("account_type", ["string", "null"], "The account's plan, as Jotform gives it."),
            _out("status", ["string", "null"], "The account's status."),
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "check_readiness",
        "title": "Check readiness",
        "kind": "read",
        "calls": ["GET /user", "GET /user/usage", "GET /user/forms"],
        "description": (
            "Says for every everyday step whether it works with this key and account, and "
            "what to set up if not. Reads only."
        ),
        "inputs": [],
        "outputs": [
            _out("ready", "boolean", "True when every everyday step works."),
            _out(
                "steps",
                "array",
                "One row per step: operation_id, title, status (works, needs_setup, "
                "not_available), reason and action.",
                items={"type": "object"},
            ),
            _out(
                "account",
                "object",
                "The region, plan, status, API calls left and what each check answered.",
                additionalProperties=True,
            ),
            WARNINGS,
        ],
    },
    {
        "operation_id": "build_support_report",
        "title": "Build support report",
        "kind": "read",
        "calls": ["GET /user", "GET /user/usage", "GET /user/forms"],
        "description": (
            "Saves a JSON file for a support request: the extension version, the region, the "
            "readiness check and the failed step's error. It holds no records and no API key; "
            "e-mail addresses and long numbers are masked."
        ),
        "inputs": [
            _text(
                "failed_operation_id",
                "Failed step",
                "The action id of the step that failed.",
                maxLength=100,
            ),
            _text("failed_error_code", "Error code", "The error code it returned.", maxLength=100),
            _text("failed_error", "Error", "The error text it returned.", maxLength=4000),
        ],
        "outputs": [
            _out("file", "string", "The report file.", value_type="artifact_handle"),
            _out("summary", "string", "A few lines to paste into the request."),
            _out("support_url", "string", "Where to send it."),
            WARNINGS,
        ],
    },
    {
        "operation_id": "list_forms",
        "title": "List forms",
        "kind": "read",
        "calls": ["GET /user/forms"],
        "description": (
            "Reads the account's forms page by page, in the step output or a JSON file: id, "
            "title, status, dates and the number of new and all submissions. Filter and order "
            "as the documentation describes."
        ),
        "inputs": [
            {"name": "filter", "title": "Filter", "type": "object", "description": FILTER_HELP},
            _text(
                "orderby",
                "Order by",
                "The form field to order by.",
                enum=[
                    "id",
                    "username",
                    "title",
                    "status",
                    "created_at",
                    "updated_at",
                    "new",
                    "count",
                    "slug",
                ],
            ),
            *PAGING_INPUTS,
        ],
        "outputs": [
            *PAGING_OUTPUTS,
            _out(
                "forms",
                "array",
                "The forms read (empty with output file).",
                items={"type": "object"},
            ),
            FILE_OUTPUT,
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "describe_form_questions",
        "title": "Describe form questions",
        "kind": "read",
        "calls": ["GET /form/{id}/questions"],
        "description": (
            "Lists a form's questions in their order: question id, name, label, type, whether "
            "it is required and the names of its parts (first and last of a full name). "
            "Create submission takes answers by these question ids."
        ),
        "inputs": [FORM_ID],
        "outputs": [
            _out("form_id", "string", "The form."),
            _out(
                "questions",
                "array",
                "qid, name, text, type, order, required, sub_fields.",
                items={"type": "object"},
            ),
            WARNINGS,
        ],
    },
    {
        "operation_id": "get_form_submissions_since",
        "title": "Get form submissions since",
        "kind": "read",
        "calls": ["GET /form/{id}/submissions"],
        "description": (
            "Reads a form's submissions created at or after a moment, and returns where the "
            "next run continues: give next_since as since and next_after_ids as after_ids, "
            "and each submission comes once. A run that stops early returns next_offset for "
            "the same window. Dates are written as Jotform writes them, YYYY-MM-DD HH:MM:SS."
        ),
        "inputs": [
            FORM_ID,
            _text(
                "since",
                "Since",
                "Submissions created at or after this moment, YYYY-MM-DD HH:MM:SS (or "
                "YYYY-MM-DD). Empty: from the first one.",
                maxLength=19,
            ),
            {
                "name": "after_ids",
                "title": "Already read at since",
                "type": "array",
                "items": {"type": "string"},
                "description": "Submission ids of the moment since that an earlier run returned (its next_after_ids).",
            },
            {
                "name": "filter",
                "title": "Filter",
                "type": "object",
                "description": FILTER_HELP + " Without created_at: since gives the window.",
            },
            *PAGING_INPUTS,
        ],
        "outputs": [
            _out("count", "integer", "How many submissions were read."),
            _out("complete", "boolean", "True when the whole window was read."),
            _out(
                "next_since",
                ["string", "null"],
                "Give it as since in the next run: the latest created_at read once the window "
                "was read to its end.",
            ),
            _out(
                "next_after_ids",
                "array",
                "Give them as after_ids in the next run.",
                items={"type": "string"},
            ),
            _out(
                "next_offset",
                ["integer", "null"],
                "When not complete: the offset to continue the same window at (with the same "
                "since and after_ids).",
            ),
            _out("page_size", "integer", "The records asked for per page."),
            _out(
                "submissions",
                "array",
                "The submissions read (empty with output file).",
                items={"type": "object"},
            ),
            FILE_OUTPUT,
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "get_submission_answers",
        "title": "Get submission answers",
        "kind": "read",
        "calls": ["GET /submission/{id}"],
        "description": (
            "Reads one submission: its form, dates, status and its answers in question order, "
            "each with the question's label, type, the answer and its formatted text."
        ),
        "inputs": [
            _text(
                "submission_id",
                "Submission ID",
                "The submission's id, as the submission lists give it.",
                maxLength=30,
            )
        ],
        "outputs": [
            _out("submission_id", "string", "The submission."),
            _out("form_id", ["string", "null"], "Its form."),
            _out("created_at", ["string", "null"], "When it was created."),
            _out("updated_at", ["string", "null"], "When it was last changed."),
            _out("status", ["string", "null"], "ACTIVE or OVERQUOTA."),
            _out(
                "answers",
                "array",
                "qid, name, text, type, answer, pretty.",
                items={"type": "object"},
            ),
            WARNINGS,
        ],
    },
    {
        "operation_id": "create_submission",
        "title": "Create submission",
        "kind": "write",
        "calls": ["GET /form/{id}/questions", "POST /form/{id}/submissions"],
        "description": (
            "Adds a submission to a form. Answers are given by question id; the step reads "
            "the form's questions first and refuses an id the form does not have, before "
            "anything is sent (a test run checks the inputs only). It is sent once, never "
            "repeated."
        ),
        "inputs": [
            FORM_ID,
            {
                "name": "answers",
                "title": "Answers",
                "type": "object",
                "description": (
                    'Question id → answer, for example {"3": "Hello", "2": {"first": '
                    '"Ann", "last": "Lee"}}; a part may also be given as "2_first". '
                    "Get the ids with Describe form questions."
                ),
            },
        ],
        "outputs": [
            _out("submission_id", ["string", "null"], "The new submission's id."),
            _out("form_id", ["string", "null"], "The form."),
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "download_submission_file",
        "title": "Download submission file",
        "kind": "read",
        "calls": ["GET /form/{id}/files", "GET the file's jotform.com/uploads address"],
        "description": (
            "Saves a file uploaded with a submission as a workflow file. The step finds it in "
            "the form's uploads by submission and, when there are several, by file name."
        ),
        "inputs": [
            FORM_ID,
            _text(
                "submission_id",
                "Submission ID",
                "The submission the file belongs to.",
                maxLength=30,
            ),
            _text(
                "file_name",
                "File name",
                "The file's name, needed when the submission has several files.",
                maxLength=500,
            ),
        ],
        "outputs": [
            _out("file", "string", "The saved file.", value_type="artifact_handle"),
            _out("file_name", "string", "Its name."),
            _out("content_type", ["string", "null"], "Its type, as the upload address gave it."),
            _out("size_bytes", "integer", "Its size."),
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "list_form_webhooks",
        "title": "List form webhooks",
        "kind": "read",
        "calls": ["GET /form/{id}/webhooks"],
        "description": "Lists the addresses a form sends each new submission to, with their ids.",
        "inputs": [FORM_ID],
        "outputs": [
            _out("form_id", "string", "The form."),
            _out("webhooks", "array", "webhook_id and url.", items={"type": "object"}),
            WARNINGS,
        ],
    },
    {
        "operation_id": "add_webhook_if_new",
        "title": "Add webhook if new",
        "kind": "write",
        "calls": ["GET /form/{id}/webhooks", "POST /form/{id}/webhooks"],
        "description": (
            "Makes a form send each new submission to an address, unless it already does. "
            "After adding, the list is read once more: an address added twice at the same "
            "time is reported, nothing is removed. Run it once at a time for one form."
        ),
        "inputs": [
            FORM_ID,
            _text(
                "webhook_url",
                "Webhook address",
                "The http or https address that receives the submissions.",
                maxLength=2000,
            ),
        ],
        "outputs": [
            _out(
                "created",
                ["boolean", "null"],
                "True when the webhook was added, false when it was there.",
            ),
            _out("webhook_id", ["string", "null"], "Its id in the form's list."),
            _out(
                "duplicate_detected",
                ["boolean", "null"],
                "After adding: true when the address is now there more than once; none when "
                "not checked.",
            ),
            _out(
                "duplicate_ids", "array", "The ids of the same address.", items={"type": "string"}
            ),
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
    {
        "operation_id": "remove_webhook",
        "title": "Remove webhook",
        "kind": "write",
        "calls": ["GET /form/{id}/webhooks", "DELETE /form/{id}/webhooks/{whid}"],
        "description": (
            "Stops a form from sending submissions to an address, by its id or address. When "
            "the form has no such webhook nothing is sent; an address there more than once "
            "needs its id."
        ),
        "inputs": [
            FORM_ID,
            _text("webhook_id", "Webhook ID", "Its id in the form's list, such as 0.", maxLength=6),
            _text("webhook_url", "Webhook address", "Or its address.", maxLength=2000),
        ],
        "outputs": [
            _out("removed", ["boolean", "null"], "True when it was removed."),
            _out("webhook_id", ["string", "null"], "The webhook removed."),
            _out("url", ["string", "null"], "Its address."),
            _out("remaining", ["integer", "null"], "How many webhooks the form has left."),
            LIMIT_LEFT,
            WARNINGS,
        ],
    },
]

#: Inputs an everyday step cannot run without.
REQUIRED: dict[str, frozenset[str]] = {
    "describe_form_questions": frozenset({"form_id"}),
    "get_form_submissions_since": frozenset({"form_id"}),
    "get_submission_answers": frozenset({"submission_id"}),
    "create_submission": frozenset({"form_id", "answers"}),
    "download_submission_file": frozenset({"form_id", "submission_id"}),
    "list_form_webhooks": frozenset({"form_id"}),
    "add_webhook_if_new": frozenset({"form_id", "webhook_url"}),
    "remove_webhook": frozenset({"form_id"}),
}
#: Everyday steps that may save a workflow file, and how it is filed.
FILES: dict[str, dict[str, str]] = {
    "list_forms": {"filename": "jotform-forms.json", "content_type": "application/json"},
    "get_form_submissions_since": {
        "filename": "jotform-submissions.json",
        "content_type": "application/json",
    },
    "download_submission_file": {
        "filename": "jotform-upload.bin",
        "content_type": "application/octet-stream",
        "binding": "jotform_upload",
    },
}
REPORT_FILE = {"filename": "jotform-support-report.json", "content_type": "application/json"}
