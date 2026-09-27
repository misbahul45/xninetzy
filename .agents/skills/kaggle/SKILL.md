---
name: "kaggle"
description: "Operate the authenticated Kaggle account as a Kaggle-aware agent: search datasets and notebooks, download CSV/Parquet/JSON/SQLite into the local workspace, profile and validate files locally, monitor notebook execution status, and pull notebook source. Use whenever an agent wants to discover Kaggle datasets, inspect a dataset's schema before committing to a download, profile a downloaded file, audit its data quality, or check the status of a Kaggle notebook execution. Applies when the user asks for an ecommerce / academic / ML dataset from Kaggle, wants to compare notebooks, or needs to attach a Kaggle dataset to an analysis. Do not use to execute or push Kaggle notebooks unless the operator has explicitly enabled mutation and supplied an approval_id."
metadata:
  scope: "general"
  owner: "xninetzy"
  language: "en"
  version: "1.0.0"
  lifecycle: "auth-check -> search -> inspect -> download -> profile -> validate -> (optional) notebook-status"
  triggers: "kaggle dataset notebook kernel csv parquet profile validate status pull run push olistbr ecommerce"
---

## Kaggle Integration — Operating Notes

Use the `kaggle_auth_status` tool first to confirm the operator's credentials and provider availability. If unauthenticated, surface `KAGGLE_AUTH_REQUIRED` with the configured `next_steps` and stop.

For dataset discovery, prefer `kaggle_dataset_search` (paginated) followed by `kaggle_dataset_get` (single metadata) and `kaggle_dataset_files` (filename enumeration). Only call `kaggle_dataset_download` after the operator has approved the dataset and the desired file(s) are known.

Local file inspection happens entirely inside the Kaggle workspace (`KAGGLE_WORKSPACE_DIR`, default `~/.local/share/xninetzy/kaggle`). Use `kaggle_dataset_schema` for compact column dtypes, `kaggle_dataset_preview` for first rows, `kaggle_dataset_profile` for richer statistics, and `kaggle_dataset_validate` for data-quality findings.

Notebook operations treat the kernel as the primary resource. `kaggle_notebook_pull` fetches the source; `kaggle_notebook_source` parses the `.ipynb` into a cell list bounded by `KAGGLE_MAX_INSPECT_BYTES`. Notebook execution (`kaggle_notebook_run`) is mutating and gated by `KAGGLE_REQUIRE_CONFIRMATION_FOR_RUN` and an explicit `approval_id`.

All credential material is read from `KAGGLE_USERNAME` + `KAGGLE_KEY`, `KAGGLE_API_TOKEN`, or `KAGGLE_CONFIG_DIR/kaggle.json`. Never accept credentials as tool arguments. All tool output is passed through `sanitize_tool_output` and `strip_trusted_context` to ensure secret redaction.
