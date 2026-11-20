"""The everyday steps, built on the documented operations of the Jotform API.

Each one goes through the same transport as the generated steps, so the API key
handling, the pace, the rate-limit rule and the reading of refusals are the same, and
every write's outcome is decided by ``outcome.write_outcome`` (table T).

Lists are read in whole pages with ``offset`` and ``limit`` (the documentation: "Start
of each result set … Default is 0", "Number of results in each result set … Maximum is
1000"). A list is complete when a page comes back shorter than asked; the answers carry
no total, so there is no "more counted" to compare with. A read stops when the asked
maximum is reached, the step output (or the workflow file) is full or time is short;
it then returns what it read with ``complete`` false and the offset of the first record
it did not read. Each page asks at most the records still wanted (``page_size`` or the
rest of ``max_records``, whichever is smaller), so ``max_records`` holds for the first
page too and ``next_offset`` continues exactly. A page too large for the output is asked again at half the size, the
next one at the full size again.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from . import budget, errors, files, generic, outcome
from .context import Context
from .errors import ExtensionError, invalid
from .params import integer, jotform_time, json_object, text
from .transport import FORM, MIN_CALL_WINDOW_SECONDS, Call, DeadlineReached, dumps_json

FILE_CONTENT_TYPE = "application/json"
MAX_FILE_BYTES = files.MAX_DOWNLOAD_BYTES - 1024
#: The documented maximum of ``limit`` for the form and submission lists.
PAGE_SIZE = 1000
#: Room for the warning a list step adds after its last page.
LAST_WARNING_ROOM = "x" * 400
#: The most a list step's numbers (count, next_offset) can be.
MAX_LIST_RECORDS = 100_000
MAX_OFFSET = 10_000_000
#: How many times one run asks a page again at half the size.
MAX_SMALLER_PAGES = 12
_ID_RE = re.compile(r"^[0-9]{1,30}$")
_QID_KEY_RE = re.compile(r"^([0-9]{1,6})(_[A-Za-z0-9]{1,40})?$")
_SUB_KEY_RE = re.compile(r"^[A-Za-z0-9_]{1,40}$")
_WEBHOOK_ID_RE = re.compile(r"^[0-9]{1,6}$")
MAX_URL_LENGTH = 2000
#: Hosts of the files Jotform gives for uploads (the form uploads documentation).
UPLOAD_HOST_SUFFIX = ".jotform.com"


# -- helpers -----------------------------------------------------------------------------


def _closed(given: Mapping[str, Any], allowed: set[str]) -> dict[str, Any]:
    rest = {k: v for k, v in given.items() if k != "connection_ref"}
    unknown = sorted(set(rest) - allowed)
    if unknown:
        raise invalid(f"The step input has unknown fields: {', '.join(unknown[:10])}")
    return rest


def _entry(operation_id: str) -> dict[str, Any]:
    return generic.spec(operation_id)


def _bad(shown: str, what: str) -> ExtensionError:
    return errors.no_effect(
        errors.INVALID_RESPONSE,
        f"Jotform's answer to {shown} {what}",
        failure_class="provider",
        retryable=False,
    )


def get(
    context: Context,
    path: str,
    query: list[tuple[str, str]] | None = None,
    *,
    documented_as: str,
) -> dict[str, Any]:
    """One read: ``data`` (``content``), ``result_set``, ``limit_left``."""
    entry = _entry(documented_as)
    shown = f"GET {entry['path']}"
    call = Call(
        method="GET",
        path=path,
        shown=shown,
        query=tuple(query or ()),
        refusals=entry["refusals"],
        success=tuple(entry["success"]),
    )
    answer = context.transport.read(call)
    return generic.read_answer(context, answer, shown)


def send(
    context: Context,
    method: str,
    path: str,
    *,
    documented_as: str,
    form: list[tuple[str, str]] | None = None,
    step: str = outcome.CONFIRM,
    find_id: Callable[[Any], str | None] | None = None,
    what: str = "record",
) -> tuple[int, dict[str, Any]]:
    """One change, sent once; the status and its outcome as ``outcome.write_outcome``
    decides it."""
    entry = _entry(documented_as)
    shown = f"{method} {entry['path']}"
    body = urlencode(form).encode("ascii") if form else (b"" if method in {"POST", "PUT"} else None)
    call = Call(
        method=method,
        path=path,
        shown=shown,
        body=body,
        content_type=FORM,
        refusals=entry["refusals"],
        success=tuple(entry["success"]),
    )
    answer = context.transport.write(call)
    decided = outcome.write_outcome(
        context, answer, shown, entry=entry, step=step, find_id=find_id, what=what
    )
    return answer.status, decided


def _processing(decided: Mapping[str, Any]) -> dict[str, Any]:
    return {key: decided[key] for key in ("processing", "applied", "check")}


def _room(context: Context) -> bool:
    """Whether another page can still be started and read in time."""
    return context.transport.remaining() >= MIN_CALL_WINDOW_SECONDS + 15


def _opt_int(given: Mapping[str, Any], name: str, *, default: int, low: int, high: int) -> int:
    value = given.get(name)
    if value is None or value == "":
        return default
    return integer({"minimum": low, "maximum": high}, value, name)


def _choice(given: Mapping[str, Any], name: str, allowed: tuple[str, ...], default: str) -> str:
    value = given.get(name)
    if value in (None, ""):
        return default
    if value not in allowed:
        raise invalid(f"{name} must be one of: {', '.join(allowed)}")
    return str(value)


def numeric_id(value: Any, what: str) -> str:
    """A form or submission id: digits only (the documentation's examples)."""
    shown = text(value, what, max_length=30)
    if not _ID_RE.fullmatch(shown):
        raise invalid(f"{what} must be the digits of a Jotform id, such as 30693660548966")
    return shown


def _segment(value: str) -> str:
    return quote(value, safe="")


# -- account -----------------------------------------------------------------------------


def account(context: Context) -> dict[str, Any]:
    read = get(context, "/user", documented_as="get_account")
    data = read["data"]
    if not isinstance(data, Mapping) or not isinstance(data.get("username"), str):
        raise _bad("GET /user", "carries no username")
    return {**dict(data), "_limit_left": read["limit_left"]}


def test_connection(context: Context) -> dict[str, Any]:
    _closed(context.operation_input, set())
    acc = account(context)
    return {
        "connected": True,
        "region": context.connection.region,
        "username": errors.safe_text(acc.get("username"), 100),
        "name": errors.safe_text(acc.get("name"), 200) or None,
        "account_type": errors.safe_text(acc.get("account_type"), 300) or None,
        "status": errors.safe_text(acc.get("status"), 40) or None,
        "limit_left": acc.get("_limit_left"),
        "warnings": [],
    }


# -- pages ---------------------------------------------------------------------------------


class Pages:
    """Collects the records of a paged read into the step output or a workflow file."""

    def __init__(self, to_file: bool, skeleton: Mapping[str, Any], key: str) -> None:
        self.to_file = to_file
        self.skeleton = dict(skeleton)
        self.key = key
        self.items: list[Any] = []
        self.size = 2
        self.warnings: list[str] = []

    def fits(self, page: list[Any]) -> bool:
        """Whether ``page`` fits with what was already taken (nothing is added).

        The step output is measured as the whole result the step returns: every output
        at its largest, the warnings and room for the last warning, so the final budget
        check never refuses what was taken here."""
        if self.to_file:
            size = self.size + sum(len(dumps_json(item).encode("utf-8")) + 1 for item in page)
            return size <= MAX_FILE_BYTES
        items = self.items + page
        whole = dict(self.skeleton)
        whole[self.key] = items
        if "next_after_ids" in whole:
            whole["next_after_ids"] = [str(i.get("id")) for i in items if isinstance(i, Mapping)]
        whole["warnings"] = [*self.warnings, LAST_WARNING_ROOM]
        return budget.fits(whole)

    def take(self, page: list[Any]) -> bool:
        if not self.fits(page):
            return False
        if self.to_file:
            self.size += sum(len(dumps_json(item).encode("utf-8")) + 1 for item in page)
        self.items += page
        return True


def _output_choice(given: Mapping[str, Any]) -> bool:
    return _choice(given, "output", ("step", "file"), "step") == "file"


def read_pages(
    context: Context,
    *,
    path: str,
    query: list[tuple[str, str]],
    key: str,
    skeleton: Mapping[str, Any],
    given: Mapping[str, Any],
    documented_as: str,
    select: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Whole pages from ``start_offset``; ``count``, ``complete``, ``next_offset``,
    ``page_size``, ``key``, ``file``, ``limit_left``, ``warnings``."""
    start = _opt_int(given, "start_offset", default=0, low=0, high=MAX_OFFSET)
    most = _opt_int(given, "max_records", default=10_000, low=1, high=MAX_LIST_RECORDS)
    size0 = _opt_int(given, "page_size", default=PAGE_SIZE, low=1, high=PAGE_SIZE)
    pages = Pages(_output_choice(given), skeleton, key)
    offset, size = start, size0
    first = True
    complete = False
    stopped = ""
    seen: set[Any] = set()
    smaller = 0
    left: int | None = None
    shown = f"GET {_entry(documented_as)['path']}"
    while True:
        if len(pages.items) >= most:
            stopped = f"the {most} asked for were read"
            break
        if not first and not _room(context):
            stopped = "time ran out"
            break
        ask = min(size, most - len(pages.items))
        try:
            read = get(
                context,
                path,
                [*query, ("offset", str(offset)), ("limit", str(ask))],
                documented_as=documented_as,
            )
        except DeadlineReached:
            if first:
                raise
            stopped = "time ran out"
            break
        left = read["limit_left"] if read["limit_left"] is not None else left
        records = read["data"]
        if not isinstance(records, list) or not all(isinstance(r, Mapping) for r in records):
            if first:
                raise _bad(shown, "is not the documented list")
            pages.warnings.append(
                f"The answer to {shown} at offset {offset} is not the documented list; "
                "reading stopped there"
            )
            stopped = "an answer was not in the documented form"
            break
        rows = [dict(r) for r in records]
        fresh = []
        for record in rows:
            ident = record.get("id")
            if ident is not None and ident in seen:
                continue
            seen.add(ident)
            fresh.append(record)
        if len(fresh) != len(rows):
            pages.warnings.append(
                f"{len(rows) - len(fresh)} records appeared twice because the list changed "
                "while it was read; each is returned once"
            )
        kept = select(fresh) if select is not None else fresh
        if not pages.fits(kept):
            if ask > 1 and smaller < MAX_SMALLER_PAGES:
                # Ask the same records again in a page half the size; offsets count
                # records, so nothing is skipped or read twice.
                for record in fresh:
                    seen.discard(record.get("id"))
                size = max(1, ask // 2)
                if not smaller:
                    # Said at once, so the measure of what fits counts it.
                    pages.warnings.append(
                        "A page of records was too large for the output and was read in "
                        "smaller pages"
                    )
                smaller += 1
                continue
            if first:
                raise budget.too_large()
            stopped = "the output is full" if not pages.to_file else "the file is full"
            break
        pages.take(kept)
        first = False
        offset += len(rows)
        if len(rows) < ask:
            complete = True
            break
        if size != size0:
            size = size0
    if not complete:
        pages.warnings.append(
            f"Stopped early because {stopped}; run the step again from next_offset {offset} "
            "for the rest"
        )
    result: dict[str, Any] = {
        "count": len(pages.items),
        "complete": complete,
        "next_offset": None if complete else offset,
        "page_size": size0,
    }
    if pages.to_file:
        handle = None
        if pages.items:
            handle = files.save(
                context,
                dumps_json(pages.items).encode("utf-8"),
                content_type=FILE_CONTENT_TYPE,
                what="The list",
            )
        result[key] = []
        result["file"] = handle
    else:
        result[key] = pages.items
        result["file"] = None
    result["limit_left"] = left
    result["warnings"] = pages.warnings
    result["_items"] = pages.items
    result["_offset"] = offset
    return result


_ORDER_FORMS = (
    "id",
    "username",
    "title",
    "status",
    "created_at",
    "updated_at",
    "new",
    "count",
    "slug",
)
_LIST_INPUTS = {"filter", "orderby", "start_offset", "max_records", "page_size", "output"}
LIST_SKELETON = {
    "count": MAX_LIST_RECORDS,
    "complete": False,
    "next_offset": MAX_OFFSET,
    "page_size": PAGE_SIZE,
    "file": None,
    "limit_left": 10**9,
}


def list_forms(context: Context) -> dict[str, Any]:
    given = _closed(context.operation_input, _LIST_INPUTS)
    query: list[tuple[str, str]] = []
    if given.get("filter") not in (None, {}):
        query.append(("filter", dumps_json(json_object(given["filter"], "filter"))))
    if given.get("orderby") not in (None, ""):
        query.append(("orderby", _choice(given, "orderby", _ORDER_FORMS, "id")))
    result = read_pages(
        context,
        path="/user/forms",
        query=query,
        key="forms",
        skeleton={**LIST_SKELETON, "forms": []},
        given=given,
        documented_as="get_forms",
    )
    result.pop("_items")
    result.pop("_offset")
    budget.ensure_fits(result)
    return result


# -- questions -----------------------------------------------------------------------------


def questions(context: Context, form_id: str) -> dict[str, dict[str, Any]]:
    read = get(context, f"/form/{_segment(form_id)}/questions", documented_as="get_form_questions")
    data = read["data"]
    if isinstance(data, list) and not data:
        return {}
    if not isinstance(data, Mapping) or not all(isinstance(v, Mapping) for v in data.values()):
        raise _bad("GET /form/{id}/questions", "is not the documented object of questions")
    return {str(k): dict(v) for k, v in data.items()}


def _order(value: Any) -> int:
    shown = str(value)
    return int(shown) if shown.isdigit() else 10**9


def describe_form_questions(context: Context) -> dict[str, Any]:
    given = _closed(context.operation_input, {"form_id"})
    form_id = numeric_id(given.get("form_id"), "form_id")
    rows = []
    for qid, q in questions(context, form_id).items():
        sub = q.get("sublabels")
        rows.append(
            {
                "qid": str(q.get("qid", qid)),
                "name": q.get("name"),
                "text": q.get("text"),
                "type": q.get("type"),
                "order": q.get("order"),
                "required": q.get("required"),
                "sub_fields": sorted(str(k) for k in sub) if isinstance(sub, Mapping) else [],
            }
        )
    rows.sort(key=lambda r: (_order(r["order"]), _order(r["qid"])))
    result = {"form_id": form_id, "questions": rows, "warnings": []}
    budget.ensure_fits(result)
    return result


# -- submissions -------------------------------------------------------------------------

_SINCE_INPUTS = {
    "form_id",
    "since",
    "after_ids",
    "filter",
    "start_offset",
    "max_records",
    "page_size",
    "output",
}
_TIME_FORM = "%Y-%m-%d %H:%M:%S"


def _moment(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, _TIME_FORM)
    except ValueError:
        return None


def _since(given: Mapping[str, Any]) -> tuple[datetime | None, list[str]]:
    since = given.get("since")
    moment: datetime | None = None
    if since not in (None, ""):
        shown = jotform_time(since, "since")
        if len(shown) == 10:
            shown += " 00:00:00"
        moment = datetime.strptime(shown, _TIME_FORM)
    after = given.get("after_ids")
    ids: list[str] = []
    if after not in (None, [], ""):
        if moment is None:
            raise invalid("after_ids needs since: they are the submissions read at that moment")
        if not isinstance(after, list) or len(after) > 10_000:
            raise invalid("after_ids must be a list of at most 10000 submission ids")
        ids = [numeric_id(i, f"after_ids item {n}") for n, i in enumerate(after, 1)]
    return moment, ids


def get_form_submissions_since(context: Context) -> dict[str, Any]:
    """Submissions created at or after ``since`` (the ids in ``after_ids`` excluded),
    with the cursor for the next run: ``next_since`` and ``next_after_ids``.

    The window is asked with the documented filter ``created_at:gt`` one second before
    ``since`` (the answers write seconds), so the submissions of the moment ``since``
    itself are in it; those named in ``after_ids`` were read before and are left out.
    A submission older than ``since`` that comes back anyway is left out too. Once the
    window was read to its end, the cursor is the latest ``created_at`` read, and the ids
    of that moment are read once more on their own (every page of that second), so the
    cursor holds every submission of that second, also those an earlier run of the same
    window returned. If that read fails or is not read to its end, the run is not
    complete and the cursor stays where it was. When the run stops early the cursor
    stays where it was and ``next_offset`` continues the same window."""
    given = _closed(context.operation_input, _SINCE_INPUTS)
    form_id = numeric_id(given.get("form_id"), "form_id")
    moment, after_ids = _since(given)
    flt: dict[str, Any] = {}
    if given.get("filter") not in (None, {}):
        flt = json_object(given["filter"], "filter")
        if any(k.split(":", 1)[0] == "created_at" for k in flt):
            raise invalid("filter may not hold created_at: the window is given by since")
    if moment is not None:
        flt["created_at:gt"] = (moment - timedelta(seconds=1)).strftime(_TIME_FORM)
    query: list[tuple[str, str]] = []
    if flt:
        query.append(("filter", dumps_json(flt)))
    query.append(("orderby", "created_at"))
    skipped = {"older": 0, "read": 0, "undated": 0}
    known = set(after_ids)

    def select(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept = []
        for row in rows:
            when = _moment(row.get("created_at"))
            if when is None:
                skipped["undated"] += 1
                kept.append(row)
                continue
            if moment is not None and when < moment:
                skipped["older"] += 1
                continue
            if moment is not None and when == moment and str(row.get("id")) in known:
                skipped["read"] += 1
                continue
            kept.append(row)
        return kept

    result = read_pages(
        context,
        path=f"/form/{_segment(form_id)}/submissions",
        query=query,
        key="submissions",
        skeleton={
            **LIST_SKELETON,
            "submissions": [],
            "next_since": "2000-01-01 00:00:00",
            "next_after_ids": [],
        },
        given=given,
        documented_as="get_form_submissions",
        select=select,
    )
    items: list[dict[str, Any]] = result.pop("_items")
    warnings: list[str] = result["warnings"]
    if skipped["older"]:
        warnings.append(
            f"{skipped['older']} submissions older than since came back and are left out"
        )
    if skipped["undated"]:
        warnings.append(
            f"{skipped['undated']} submissions have no created_at in the documented form; "
            "they are returned but do not move the cursor"
        )
    since_text = moment.strftime(_TIME_FORM) if moment is not None else None
    next_since, next_ids = since_text, list(after_ids)
    if result["complete"]:
        dated = [w for r in items if (w := _moment(r.get("created_at")))]
        if dated:
            latest = max(dated)
            ids, failed = _ids_of_second(context, form_id, flt, latest)
            if not failed:
                trial = {k: v for k, v in result.items() if not k.startswith("_")}
                trial["next_since"] = latest.strftime(_TIME_FORM)
                trial["next_after_ids"] = ids
                trial["warnings"] = [*warnings, LAST_WARNING_ROOM]
                if not budget.fits(trial):
                    failed = "its ids do not fit the step output"
            if failed:
                result["complete"] = False
                result["next_offset"] = result["_offset"]
                warnings.append(
                    f"The window was read to its end, but the submissions of its latest "
                    f"second {latest.strftime(_TIME_FORM)} could not be read for the cursor "
                    f"({failed}); the cursor stays where it was: run the step again from "
                    f"next_offset {result['_offset']} with the same since and after_ids"
                )
            else:
                next_since, next_ids = latest.strftime(_TIME_FORM), ids
    result["next_since"] = next_since
    result["next_after_ids"] = next_ids
    ordered = {
        "count": result["count"],
        "complete": result["complete"],
        "next_since": result["next_since"],
        "next_after_ids": result["next_after_ids"],
        "next_offset": result["next_offset"],
        "page_size": result["page_size"],
        "submissions": result["submissions"],
        "file": result["file"],
        "limit_left": result["limit_left"],
        "warnings": warnings,
    }
    budget.ensure_fits(ordered)
    return ordered


#: The most ids one second can give the cursor (the most ``after_ids`` takes).
MAX_AFTER_IDS = 10_000


def _ids_of_second(
    context: Context, form_id: str, flt: Mapping[str, Any], latest: datetime
) -> tuple[list[str], str]:
    """The ids of every submission created in the second ``latest`` (the window's own
    filter kept), read in whole pages to the end; or the reason they could not be."""
    second = dict(flt)
    second["created_at:gt"] = (latest - timedelta(seconds=1)).strftime(_TIME_FORM)
    second["created_at:lt"] = (latest + timedelta(seconds=1)).strftime(_TIME_FORM)
    query = [("filter", dumps_json(second)), ("orderby", "created_at")]
    path = f"/form/{_segment(form_id)}/submissions"
    shown = f"GET {_entry('get_form_submissions')['path']}"
    ids: list[str] = []
    offset = 0
    while True:
        if not _room(context):
            return [], "time ran out"
        try:
            read = get(
                context,
                path,
                [*query, ("offset", str(offset)), ("limit", str(PAGE_SIZE))],
                documented_as="get_form_submissions",
            )
        except DeadlineReached:
            return [], "time ran out"
        except ExtensionError as error:
            return [], f"{shown} failed: {error.code}"
        records = read["data"]
        if not isinstance(records, list) or not all(isinstance(r, Mapping) for r in records):
            return [], f"the answer to {shown} is not the documented list"
        for record in records:
            ident = str(record.get("id"))
            if _moment(record.get("created_at")) == latest and ident not in ids:
                ids.append(ident)
        if len(ids) > MAX_AFTER_IDS:
            return [], f"more than {MAX_AFTER_IDS} submissions share that second"
        offset += len(records)
        if len(records) < PAGE_SIZE:
            return ids, ""


def submission(context: Context, submission_id: str) -> dict[str, Any]:
    read = get(context, f"/submission/{_segment(submission_id)}", documented_as="get_submission")
    data = read["data"]
    if not isinstance(data, Mapping):
        raise _bad("GET /submission/{id}", "is not the documented submission object")
    return dict(data)


def get_submission_answers(context: Context) -> dict[str, Any]:
    given = _closed(context.operation_input, {"submission_id"})
    submission_id = numeric_id(given.get("submission_id"), "submission_id")
    data = submission(context, submission_id)
    answers = []
    raw = data.get("answers")
    if isinstance(raw, Mapping):
        for qid, item in raw.items():
            if not isinstance(item, Mapping):
                continue
            answers.append(
                {
                    "qid": str(qid),
                    "name": item.get("name"),
                    "text": item.get("text"),
                    "type": item.get("type"),
                    "answer": item.get("answer"),
                    "pretty": item.get("prettyFormat"),
                }
            )
    answers.sort(key=lambda a: _order(a["qid"]))
    result = {
        "submission_id": str(data.get("id") or submission_id),
        "form_id": data.get("form_id"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "status": data.get("status"),
        "answers": answers,
        "warnings": [] if isinstance(raw, Mapping) else ["The submission carries no answers"],
    }
    budget.ensure_fits(result)
    return result


# -- create submission ---------------------------------------------------------------------


def submission_pairs(answers: Any) -> list[tuple[str, str]]:
    """``answers`` as the documented form fields: ``{"3": "x"}`` as ``submission[3]``,
    ``{"2": {"first": "A"}}`` as ``submission[2][first]`` (the operation list's form) and
    ``{"2_first": "A"}`` as ``submission[2_first]`` (the documentation's curl example)."""
    if not isinstance(answers, Mapping) or not answers:
        raise invalid("answers must be an object: question id → answer")
    pairs: list[tuple[str, str]] = []
    for key, value in answers.items():
        if not isinstance(key, str) or not _QID_KEY_RE.fullmatch(key):
            raise invalid(
                "answers keys must be question ids such as 3, or 2_first for a part of a question"
            )
        if isinstance(value, Mapping):
            if "_" in key:
                raise invalid(f"answers.{key} names a part already; give its text")
            if not value:
                raise invalid(f"answers.{key} is an empty object")
            for sub, item in value.items():
                if not isinstance(sub, str) or not _SUB_KEY_RE.fullmatch(sub):
                    raise invalid(f"answers.{key} has a part name that is not usable")
                pairs.append(
                    (f"submission[{key}][{sub}]", generic.form_value(item, f"answers.{key}.{sub}"))
                )
        else:
            pairs.append((f"submission[{key}]", generic.form_value(value, f"answers.{key}")))
        if len(pairs) > generic.MAX_FIELDS:
            raise invalid(f"answers holds more than {generic.MAX_FIELDS} fields")
    return pairs


def validate_create_submission(operation_input: Mapping[str, Any]) -> None:
    given = _closed(operation_input, {"form_id", "answers"})
    numeric_id(given.get("form_id"), "form_id")
    submission_pairs(given.get("answers"))


def _submission_id(content: Any) -> str | None:
    value = content.get("submissionID") if isinstance(content, Mapping) else None
    shown = str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else ""
    return shown if _ID_RE.fullmatch(shown) else None


def create_submission(context: Context) -> dict[str, Any]:
    validate_create_submission(context.operation_input)
    given = context.operation_input
    form_id = numeric_id(given["form_id"], "form_id")
    pairs = submission_pairs(given["answers"])
    known = questions(context, form_id)
    # The keys were checked against _QID_KEY_RE: the question id is before any "_".
    asked = {str(k).split("_", 1)[0] for k in given["answers"]}
    missing = sorted(asked - set(known), key=_order)
    if missing:
        raise invalid(
            f"Form {form_id} has no questions {', '.join(missing[:10])}; get the question ids "
            "with Describe form questions"
        )
    _, decided = send(
        context,
        "POST",
        f"/form/{_segment(form_id)}/submissions",
        documented_as="add_submission_to_form",
        form=pairs,
        step=outcome.CONFIRM_CREATE,
        find_id=_submission_id,
        what="submission",
    )
    return {
        "submission_id": decided["id"],
        "form_id": form_id,
        "limit_left": decided["limit_left"],
        **_processing(decided),
        "warnings": decided["warnings"],
    }


# -- download a file -----------------------------------------------------------------------


def _upload_url(value: Any) -> str:
    shown = value.strip() if isinstance(value, str) else ""
    parts = urlsplit(shown)
    host = (parts.hostname or "").lower()
    if (
        not shown
        or len(shown) > MAX_URL_LENGTH
        or parts.scheme not in {"http", "https"}
        or not (host == UPLOAD_HOST_SUFFIX[1:] or host.endswith(UPLOAD_HOST_SUFFIX))
        or parts.port is not None
        or parts.username is not None
        or not parts.path.startswith("/uploads/")
    ):
        raise _bad("GET /form/{id}/files", "gives a file address outside jotform.com/uploads")
    return "https://" + host + parts.path + (f"?{parts.query}" if parts.query else "")


def download_submission_file(context: Context) -> dict[str, Any]:
    given = _closed(context.operation_input, {"form_id", "submission_id", "file_name"})
    form_id = numeric_id(given.get("form_id"), "form_id")
    submission_id = numeric_id(given.get("submission_id"), "submission_id")
    wanted = given.get("file_name")
    name = None if wanted in (None, "") else text(wanted, "file_name", max_length=500)
    read = get(context, f"/form/{_segment(form_id)}/files", documented_as="get_form_uploads")
    listed = read["data"]
    if not isinstance(listed, list) or not all(isinstance(f, Mapping) for f in listed):
        raise _bad("GET /form/{id}/files", "is not the documented list of files")
    mine = [dict(f) for f in listed if str(f.get("submission_id")) == submission_id]
    if name is not None:
        mine = [f for f in mine if f.get("name") == name]
    if not mine:
        raise errors.no_effect(
            errors.NOT_FOUND,
            f"Submission {submission_id} of form {form_id} has no uploaded file"
            + (f" named {errors.safe_text(name, 100)}" if name else ""),
        )
    if len(mine) > 1:
        names = ", ".join(errors.safe_text(f.get("name"), 80) for f in mine[:10])
        raise invalid(f"The submission has {len(mine)} files ({names}): give file_name")
    chosen = mine[0]
    url = _upload_url(chosen.get("url"))
    try:
        answer = context.transport.fetch_file(url, files.MAX_DOWNLOAD_BYTES)
    except ExtensionError as exc:
        if exc.code in {errors.SETUP_REQUIRED, errors.AUTHENTICATION_FAILED}:
            raise errors.setup(
                f"The upload address refused the file (HTTP {exc.http_status}): the account may "
                "require signing in to view uploaded files, which this extension cannot do"
            ) from None
        raise
    file_name = errors.safe_text(chosen.get("name"), 300)
    if "html" in answer.content_type and not file_name.lower().endswith((".htm", ".html")):
        raise errors.setup(
            "The upload address answered with a web page, not the file: the account may "
            "require signing in to view uploaded files, which this extension cannot do"
        )
    handle = files.save(
        context,
        answer.raw,
        content_type=files.BINARY_CONTENT_TYPE,
        what="The file",
        binding_key=files.UPLOAD_BINDING,
    )
    result = {
        "file": handle,
        "file_name": file_name,
        "content_type": answer.content_type or None,
        "size_bytes": len(answer.raw),
        "limit_left": read["limit_left"],
        "warnings": [],
    }
    return result


# -- webhooks ------------------------------------------------------------------------------


def webhooks(context: Context, form_id: str) -> tuple[list[dict[str, str]], bool]:
    """The form's webhooks as ``[{webhook_id, url}]``; and whether the answer was the
    documented list (an object of id → URL, or a list of URLs; nothing as an empty list)."""
    read = get(context, f"/form/{_segment(form_id)}/webhooks", documented_as="get_form_webhooks")
    data = read["data"]
    rows: list[dict[str, str]] = []
    if isinstance(data, Mapping):
        items = list(data.items())
    elif isinstance(data, list):
        items = [(str(i), v) for i, v in enumerate(data)]
    elif data in (None, ""):
        return [], True
    else:
        return [], False
    for key, value in items:
        if not isinstance(value, str) or not _WEBHOOK_ID_RE.fullmatch(str(key)):
            return [], False
        rows.append({"webhook_id": str(key), "url": value})
    rows.sort(key=lambda r: int(r["webhook_id"]))
    return rows, True


def list_form_webhooks(context: Context) -> dict[str, Any]:
    given = _closed(context.operation_input, {"form_id"})
    form_id = numeric_id(given.get("form_id"), "form_id")
    rows, documented = webhooks(context, form_id)
    if not documented:
        raise _bad("GET /form/{id}/webhooks", "is not the documented list of webhooks")
    result = {"form_id": form_id, "webhooks": rows, "warnings": []}
    budget.ensure_fits(result)
    return result


def webhook_url(value: Any) -> str:
    shown = text(value, "webhook_url", max_length=MAX_URL_LENGTH)
    parts = urlsplit(shown)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
        raise invalid(
            "webhook_url must be an http or https address, such as https://example.com/hook"
        )
    return shown


def validate_add_webhook(operation_input: Mapping[str, Any]) -> None:
    given = _closed(operation_input, {"form_id", "webhook_url"})
    numeric_id(given.get("form_id"), "form_id")
    webhook_url(given.get("webhook_url"))


def _conflict(message: str) -> ExtensionError:
    return errors.no_effect(errors.CONFLICT, message + "; nothing was written")


def add_webhook_if_new(context: Context) -> dict[str, Any]:
    validate_add_webhook(context.operation_input)
    given = context.operation_input
    form_id = numeric_id(given["form_id"], "form_id")
    url = webhook_url(given["webhook_url"])
    rows, documented = webhooks(context, form_id)
    if not documented:
        raise _conflict(
            "The form's webhooks could not be read in the documented form, so the check for "
            "this address is incomplete"
        )
    same = [r["webhook_id"] for r in rows if r["url"] == url]
    if len(same) > 1:
        raise _conflict(
            f"The form sends to this address {len(same)} times ({', '.join(same)}); remove "
            "the extra ones first"
        )
    if same:
        return {
            "created": False,
            "webhook_id": same[0],
            "duplicate_detected": None,
            "duplicate_ids": [],
            "limit_left": None,
            **outcome.NOTHING_SENT,
            "warnings": ["The form already sends to this address; nothing was written"],
        }
    _, decided = send(
        context,
        "POST",
        f"/form/{_segment(form_id)}/webhooks",
        documented_as="add_form_webhook",
        form=[("webhookURL", url)],
    )
    warnings = list(decided["warnings"])
    # Search and add are not one step: the same address may have been added by a parallel
    # run. The check is repeated once; nothing is removed.
    try:
        again, documented = webhooks(context, form_id)
    except (ExtensionError, DeadlineReached):
        again, documented = [], False
    if not documented:
        warnings.append(
            "The webhook was added, but the check for the same address added at the same "
            "time could not be repeated"
        )
        detected: bool | None = None
        ids: list[str] = []
        new_id = None
    else:
        ids = [r["webhook_id"] for r in again if r["url"] == url]
        new_id = ids[-1] if ids else None
        detected = len(ids) > 1
        if detected:
            warnings.append(
                "The address is now there more than once (a parallel run): duplicate_ids "
                "lists them; nothing was removed"
            )
        if not ids:
            warnings.append("The webhook was added but the repeated check does not show it")
    return {
        "created": True,
        "webhook_id": new_id,
        "duplicate_detected": detected,
        "duplicate_ids": ids if detected else [],
        "limit_left": decided["limit_left"],
        **_processing(decided),
        "warnings": warnings,
    }


def validate_remove_webhook(operation_input: Mapping[str, Any]) -> None:
    given = _closed(operation_input, {"form_id", "webhook_id", "webhook_url"})
    numeric_id(given.get("form_id"), "form_id")
    has_id = given.get("webhook_id") not in (None, "")
    has_url = given.get("webhook_url") not in (None, "")
    if has_id == has_url:
        raise invalid("Give webhook_id or webhook_url, one of them")
    if has_id:
        shown = text(given["webhook_id"], "webhook_id", max_length=6)
        if not _WEBHOOK_ID_RE.fullmatch(shown):
            raise invalid("webhook_id must be the webhook's number, such as 0")
    else:
        webhook_url(given["webhook_url"])


def remove_webhook(context: Context) -> dict[str, Any]:
    validate_remove_webhook(context.operation_input)
    given = context.operation_input
    form_id = numeric_id(given["form_id"], "form_id")
    rows, documented = webhooks(context, form_id)
    if not documented:
        raise _conflict(
            "The form's webhooks could not be read in the documented form, so which one to "
            "remove is not certain"
        )
    if given.get("webhook_id") not in (None, ""):
        wanted = str(given["webhook_id"]).strip()
        found = [r for r in rows if r["webhook_id"] == wanted]
    else:
        url = webhook_url(given["webhook_url"])
        found = [r for r in rows if r["url"] == url]
    if len(found) > 1:
        ids = ", ".join(r["webhook_id"] for r in found)
        raise _conflict(f"{len(found)} webhooks send to this address ({ids}): give webhook_id")
    if not found:
        return {
            "removed": False,
            "webhook_id": None,
            "url": None,
            "remaining": len(rows),
            "limit_left": None,
            **outcome.NOTHING_SENT,
            "warnings": ["The form has no such webhook; nothing was changed"],
        }
    target = found[0]
    _, decided = send(
        context,
        "DELETE",
        f"/form/{_segment(form_id)}/webhooks/{_segment(target['webhook_id'])}",
        documented_as="delete_form_webhook",
    )
    content = decided.get("data")
    remaining = len(content) if isinstance(content, (Mapping, list)) else None
    return {
        "removed": True,
        "webhook_id": target["webhook_id"],
        "url": target["url"],
        "remaining": remaining,
        "limit_left": decided["limit_left"],
        **_processing(decided),
        "warnings": decided["warnings"],
    }


# -- registry ------------------------------------------------------------------------------

COMPOSITES: dict[str, Callable[[Context], dict[str, Any]]] = {
    "test_connection": test_connection,
    "list_forms": list_forms,
    "describe_form_questions": describe_form_questions,
    "get_form_submissions_since": get_form_submissions_since,
    "get_submission_answers": get_submission_answers,
    "create_submission": create_submission,
    "download_submission_file": download_submission_file,
    "list_form_webhooks": list_form_webhooks,
    "add_webhook_if_new": add_webhook_if_new,
    "remove_webhook": remove_webhook,
}
COMPOSITE_WRITES: frozenset[str] = frozenset(
    {"create_submission", "add_webhook_if_new", "remove_webhook"}
)
VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "create_submission": validate_create_submission,
    "add_webhook_if_new": validate_add_webhook,
    "remove_webhook": validate_remove_webhook,
}
#: Everyday steps that may save a workflow file.
FILE_OUTPUT_IDS: frozenset[str] = frozenset(
    {"list_forms", "get_form_submissions_since", "download_submission_file"}
)

__all__ = [
    "COMPOSITES",
    "COMPOSITE_WRITES",
    "FILE_OUTPUT_IDS",
    "VALIDATORS",
    "numeric_id",
    "read_pages",
    "submission_pairs",
]
