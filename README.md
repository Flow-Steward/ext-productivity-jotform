# Jotform integration for Flow Steward

<img src="icon.png" width="96" alt="Jotform integration for Flow Steward">

[![CI](https://img.shields.io/github/actions/workflow/status/brizzl/ext-productivity-jotform/ci.yml?branch=main&label=CI)](https://github.com/brizzl/ext-productivity-jotform/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/brizzl/ext-productivity-jotform?label=release)](https://github.com/brizzl/ext-productivity-jotform/releases/latest)

Automate Jotform with Flow Steward workflows and AI agents: pick up new form submissions, pass them to other systems, create submissions and manage webhooks — without writing code.

This Flow Steward extension is a Jotform integration for form and survey automation. It works through the Jotform REST API of your account: it reads forms and their questions, reads new submissions with a cursor that continues where the last run stopped, creates submissions, saves uploaded files and manages the webhooks of a form.

## What is this

Jotform is an online form builder for forms, surveys, registrations and orders. This extension is a connector: it adds ready Jotform steps to the Flow Steward workflow editor and the same operations as tools for AI agents. Read more about Flow Steward at <https://docs.flowsteward.org>.

## What you can automate

- Every hour, read the new submissions of a form and pass them to a CRM, a spreadsheet or a ticket system — each submission once.
- Save the files people upload with a form into the workflow, for example to attach them to a record elsewhere.
- Create a submission in a Jotform form from data that arrives elsewhere, for example to keep one register.
- Make a form send each new submission to a workflow's address, and remove that webhook again.
- Export the account's forms into a JSON file.

## Why teams use it

- **Each submission once.** **Get form submissions since** returns `next_since` and `next_after_ids`; the next run gives them back and gets only what is new, also when several submissions share one second.
- **Whole pages only.** A list that does not fit the step output stops at a page boundary and says where to continue (`next_offset`), so no record is skipped.
- **Confirmed changes only.** Jotform confirms a change inside its answer (`responseCode` 200); an answer without it leaves the change unknown, to check before running the step again.
- **A change is not sent twice.** Changes are never retried automatically, and a test run sends none. **Add webhook if new** does nothing when the form already sends to the address.
- **The documented API is covered.** 64 steps: 12 everyday steps plus a step for 52 operations of the Jotform API documentation's 56; the **Coverage** page lists the four left out and why.
- **The key stays secret.** The API key travels only in the request header and is removed from every answer, log line and error.

## What's inside

Everyday steps:

- **Test connection** — checks the key and the region and returns the account.
- **Check readiness** — says which steps work with this key.
- **Build support report** — a file for a support request, without records or the key.
- **List forms** — the account's forms, into the step output or a JSON file.
- **Describe form questions** — question ids, labels and types, in form order.
- **Get form submissions since** — new submissions with the cursor for the next run.
- **Get submission answers** — one submission with its answers in question order.
- **Create submission** — answers by question id, checked against the form first.
- **Download submission file** — a file uploaded with a submission, as a workflow file.
- **List form webhooks**, **Add webhook if new** and **Remove webhook**.

52 operations of the documentation are also available as steps: forms, questions and properties, submissions, webhooks, reports, labels, folders, the account and its settings. The extension's **Coverage** page sums them up.

## Get started

1. In Flow Steward, open **Extensions → Catalog**, find **Jotform** and install it.
2. In Jotform, open **My Account → API** and create a key; give it full access if workflows will add submissions or webhooks.
3. On the extension's **Connection** page, choose the account's region (standard, EU or HIPAA) and paste the key. Press **Test connection**, then run **Check readiness**.
4. Build your first workflow: for example, every hour → **Get form submissions since** with the last run's `next_since` → send each submission on.

## Requirements

- A Jotform account and an API key from My Account → API. A key with read access reads only.
- Jotform counts the API calls of a key per day: 1,000 on the starter plan, 10,000 bronze, 50,000 silver, 100,000 gold (the API documentation's FAQ). Every step returns what is left (`limit_left`).
- Flow Steward 0.9.16 or later.

## FAQ

**How do I send new Jotform submissions to another system automatically?**
Run **Get form submissions since** on a schedule. Give it the `next_since` and `next_after_ids` of the last run; it returns only the new submissions.

**Does it work with EU and HIPAA accounts?**
Yes. Choose the region in the connection: EU accounts use eu-api.jotform.com, HIPAA accounts hipaa-api.jotform.com.

**How do I get the files people uploaded?**
Use **Download submission file** with the form and the submission; when the submission has several files, give the file name.

**Which Jotform API operations are supported?**
52 operations of the API documentation's 56 have their own step. Signing in with a username and password and signing out are left out (a connection uses an API key), and so are reading all labels and creating a folder, whose documentation contradicts itself.

## In your language

Интеграция Jotform с Flow Steward автоматизирует работу с онлайн-формами без программирования. Расширение работает через REST API Jotform: читает формы и их вопросы, забирает новые ответы с курсором для следующего запуска, создаёт ответы, сохраняет загруженные файлы и управляет вебхуками формы. Для подключения нужен API-ключ из My Account → API и регион аккаунта (стандартный, EU или HIPAA).

## Links

- Flow Steward documentation: <https://docs.flowsteward.org>
- Flow Steward extension catalog: <https://github.com/Flow-Steward/extensions>
- Issues and support: <https://github.com/brizzl/ext-productivity-jotform/issues>
- Jotform API documentation: <https://api.jotform.com/docs/>
- Changes: [CHANGELOG.md](CHANGELOG.md)

## For developers

The generated steps come from the operation list the Jotform API documentation page loads, pinned in `tests/reference/pinned/jotform_request_models.js` (with the page's own client, `jotform_method_section_view.js`, which shows how each parameter is sent). The facts are extracted into `tests/reference/jotform_api.json`. To check them against the documentation page itself, save `https://api.jotform.com/docs/` as `tests/reference/sources/jotform_api_docs.html` (not committed). To rebuild:

```bash
python3 -I tests/reference/extract_reference.py
python3 tests/reference/build_contracts.py
```

From a Flow Steward checkout (the checks run in the `fs-audit` container):

```bash
./core/entrypoints/cli/scripts/lint.sh --checks extension-static,extension-tests --extension-root "$PWD/workspace/extensions/com_brizzl_jotform"
./flow-steward extensions validate com.brizzl.jotform --root workspace/extensions --health --marketplace
./flow-steward extensions test com.brizzl.jotform --root workspace/extensions
```

Jotform and its marks belong to Jotform Inc.; see [BRANDING.md](BRANDING.md) for the icon's source.
