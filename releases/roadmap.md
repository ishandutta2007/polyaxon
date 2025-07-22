---
title: "Roadmap"
sub_link: "roadmap"
code_link: "https://github.com/polyaxon/polyaxon/blob/master/releases/roadmap.md"
meta_title: "Polyaxon Roadmap and upcoming release notes - Polyaxon Releases"
meta_description: "Polyaxon roadmap, release notes, migrations, and deprecation notes."
visibility: public
status: published
tags:
  - reference
sidebar: "releases"
---

## Upcoming features and enhancements

### Core

 * **New**: Add support for Alibaba Cloud (Aliyun) Object Storage System (OSS).
 * **New**: Add support for HuggingFace (huggingface_hub) `hf://` filesystem.
 * **New**: Add logic to enforce outputs validation.
 * **New**: Allow connecting Pycharm and VSCode to Polyaxon services.
 * **Discussion**: Allow to test connection directly in the polyaxonfile before setting global connections on the cluster/agent level, issue is that users who can submit jobs will be able to mount connections that are not defined by a cluster admin.
 * **Enhancement**: Add mid-runtime update with `apply` logic.
 * **Enhancement**: Improve `modelRef` and `artifactRef` initialization process and allow passing custom init path to not force the user to know the run uuid.

### CLI

 * **Enhancement**: Collect `hash` information for uploaded artifacts in the lineage metadata.

### Hub

 * **New**: Add DVC(data version control) integration.
 * **New**: Add support for ssh connection to allow connecting VSCode and Pycharm.
 * **New**: Allow registering init containers as plugins with a hub reference.


### Client

 * **New**: Add `@component` decorator to allow declaring components based on Python functions.
   * Polyaxon CLI will automatically generate a CLI based the decorator which will allows users to reduce the boilerplate and leverage their functions directly without having to use `click` or `argparse`.
   * The decorator automatically detects `NO_OP` and becomes a pass-through.
 * **New**: Add `@op/@operation` decorator to allow invoking components programmatically.
   * The decorator automatically detects `NO_OP` and defaults to a local python function call.
 * **New**: Add support for Python type hints in the both the class and the decorator component declarations.
 * **New**: Automatically detect if the filesystem should use the stream or the artifacts store directly.

### Operator

 * **New**: Add deployments to allow starting Ray, Dask, Spark clusters.

### Docs

 * **Enhancement**: Add docs for policies.
 * **Enhancement**: Add docs for team spaces.
 * **Enhancement**: Update docs for projects and orgs settings.
 * **Enhancement**: Add docs for inspection and events debugging.
 * **Enhancement**: Add docs for multi-namespaces management.
 * **Enhancement**: Add docs for S3 ARN support.
 * **Enhancement**: Add docs for agent's annotations for service accounts scheduling.
 * **Enhancement**: Add docs for mounting connections to agents.
 * **Enhancement**: Add docs for agents monitoring and inspection features.
 * **Enhancement**: Add docs for organization's level cross-projects views for registries, runs, and analytics.
 * **Enhancement**: Add docs for switching between organizations and team-spaces.
 * **Enhancement**: Add docs for saving analytics views.
 * **Enhancement**: Add docs for the pushing/pulling runs and viewing local runs.
 * **Enhancement**: Add docs for integrations.
 * **Enhancement**: Add docs for automations.
 * **Enhancement**: Add docs for incoming events.

### Agent

 * **New**: Add monitoring for agent pods to quickly debug agent issues.
 * **Beta**: Add cluster and namespace monitoring:
   * Show nodes's states and health.
   * Show nodes's CPU/Memory/GPU consumption.

### Specification

 * **New**: (Beta) Multi-container pipeline orchestration in a single operation.
 * **Enhancement**: Allow setting DAG outputs without the SDK/Client.
 * **Enhancement**: Improve auto-complete plugins.

### UI

 * **New**: Add metrics/params performance widget to dashboards.
 * **New**: Add Metrics/Params correlation and importance.
 * **New**: Reports; new interface to create dashboards and shareable notes.
 * **New**: Show an indicator on artifacts lineage if it's promoted to a model version or artifact version.
 * **New**: Add connection information to artifacts lineage.
 * **New**: Add new advanced filters, allow filtering the runs in the comparison table based on:
   * parallel coordinate.
   * histogram.
   * activity calendar.
   * custom visualizations.
 * **New**: Allow comparing resources with metrics and cross runs resources.
 * **New**: Add predefined hyperparameter tuning widgets/visualizations.
 * **New**: When possible, the `?` will show a direct link to the docs relevant to the UI current page. e.g. if the user is on the service accounts setting tab the `?` will have a link to the guides related to the service accounts.
 * **New**: UI to pass parameters and check their types automatically.
 * **Enhancement**: Improve widget download to provide option to download the data in CSV format in addition to image formats.
 * **Enhancement**: Allow controlling sample size.

### Tracking

 * **New**: Allow to specify the connection name when logging assets and artifacts to associate the lineage to a specific connection.
 * **New**: Add support for logging data versions, summaries, reports, and quality.
 * **New**: Add log table.
 * **New**: Add custom bar plots.
 * **New**: Add spaCy tracking callback.
 * **New**: Add Prophet tracking callback.
 * **Beta**: Add trace/span tracking.
 * **Beta**: Add LLMs tracking logic.
 * **Enhancement**: Improve logic around assets and artifacts logging to only trigger versioned behavior (step-wise) when a step parameter is provided.
 * **Enhancement**: Improve outputs state calculation.
 * **Enhancement**: Improve artifacts names auto-generator to respect the name size limit.
 * **Enhancement**: Allow tracking dataframes as parquet files.

### Integrations

 * **New**: Add fiftyone integration.
 * **New**: Add gradio integration.
 * **New**: Add mlflow integration.
 * **New**: Add mario integration.

### Commercial

 * **New**: Add notification center to allow users to control and manage notifications using the UI.
 * **New**: Add selection reports, this is similar to selection in v0 but the new implementation will support all the new features and dashboard flexibility (events, artifacts, lineages, comparison, custom columns selection, multi-field sorting, ...):
   * Allows adding single runs to a report from the run's overview page.
   * Allows adding multiple runs to a report using a multi-run action.
   * Add project sidebar button `Reports`.
   * Allow running downstream-ops for a report, e.g. multi-run Tensorboard.
 * **Beta**: Add new queuing logic:
    * fair-share queuing
    * auto-preemption based on priority
    * auto-requeueing for suspended operations
    * per-queue preset
 * **New**: Add a new tab to explore unregistered artifact/component/model versions under each project.
 * **Enhancement**: Improve reassignment of the main organization owner.
 * **Enhancement**: Allow owner/billing users to reset the billing anchor date, several users asked to change when they get billed during month.
 * **Enhancement**: Add more informative messages and handling when scaling down usage/agents/seats or when downgrading to a plan missing a specific feature.
 * **Enhancement**: Add support for resuming pipelines and matrix operations.
 * **Enhancement**: Investigate the new `suspend` feature to provide immediate concurrency change instead of the current [draining logic](/faq/How-does-changing-concurrency-work/).
 * **Fix**: Regression in metric early stopping policies.
