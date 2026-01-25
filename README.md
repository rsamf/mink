<p align="center">
  <img src="assets/logo.png" alt="Logo" width=256>
  <p align="center">
    <sup>Image generated with Nano Banana Pro</sup>
  </p>

  <h1 align="center">Mink</h1>

  <p align="center">
    <a href="https://github.com/rsamf/mink/blob/main/LICENSE">
      <img alt="GitHub License" src="https://img.shields.io/github/license/graphbookai/graphbook">
    </a>
    <a href="https://hub.docker.com/r/rsamf/mink">
      <img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/rsamf/mink">
    </a>
  </p>

  <p align="center">
    AI Notetaker for Meetings (Open-Source Otter AI Alternative)
  </p>
</p>

## Overview

Mink is a service that lets you upload recordings of meetings, so that you can gather insights, such as
action items, a topic, and a summary, of the meeting. It extracts textual information from the video -- 
transcripts and on-screen text -- and forwards that to an LLM service. This is similar to Otter AI. Zoom
also already has some builtin features for transcripts + LLM. The value is that this is open-source.

Mink does not have any UI or frontend, only offering CLI tool to submit videos and view processing jobs.
However, all meeting data is stored in GCP Cloud SQL which offers an MCP server. That means you can easily
talk to your meeting data with supporting tools such as Claude Desktop.

#### Why I Built This?
This was a 3-day take-home assignment for a job at Roboflow. Therefore, expect a lot of missing features.

## Getting Started

First, clone the repo.

### Demo

The easiest way to start is to try the demo. **This requires an API key.**

1. Make sure the repo is clone, and change your cwd to the repo directory.
1. Install the CLI
    ```bash
    uv sync
    ```
1. Submit a meeting recording. (Tested on .mp4 files)
    ```bash
    uv run python -m mink.cli <API_KEY> submit <MEETING_FILE>
    ```

In a few seconds or minutes depending on how long the recording is, you will receive your results in 3 terminal pages. First, you'll receive the intelligent notes: topic, summary, and any available action items. Then, you'll see the raw transcript, and then, raw on-screen text.

### Run Locally with `uv` or `docker`

Before running the server locally, make sure to configure it and deploy an instance of Cloud SQL. See sections <a href="#config">Config</a> and <a href="#cloud">Cloud</a> before coming here.

#### With `uv`

1. Install server dependencies
    ```bash
    uv sync --extra server
    ```
    Or, with LightOnOCR support (Will use EasyOCR by default):
    ```bash
    uv sync --all-extras
    ```

1. Then execute it:
    ```bash
    uv run python -m mink.main
    ```

#### With `docker`
1. Build the image:
    ```bash
    docker build -t mink .
    ```
    With LightOnOCR support:

    ```bash
    docker build --build-arg sync_options="--all-extras" -t mink .
    ```
2. Then execute it:
    ```bash
    docker run --rm -d -p 8000:8000 mink
    ```

> [!TIP]
> You may get a connection error if you haven't deployed Cloud SQL yet since Mink depends on that to store its data.

## Config
Mink uses [hydra](https://hydra.cc/docs/intro/) for flexible configuration of the server.
The available configuration can be used, but it needs two extra entries to get it working:

1.
    For demo purposes, the server has a simple mechanism to restrict access to people that are "invited"
    with an API key. You can write your own api keys (e.g. "password123") into `server.auth.keys` in config/config.yaml.
    Be creative and supply it with 1 or more API keys.

1.
    If you are running the container locally, you'll need to provide the necessary Cloud SQL connection information in config/db/local.yaml. The deployed container in Cloud Run will use config/db/cloudsql.yaml which will point to the correct environment variables.

1. 
    (Optional) You may provide an Anthropic API key to gather meeting insights (i.e. "casting" raw text data to valuable insights). Only Anthropic is supported right now.
    Please, add one in config/cast/anthropic.yaml at `api_key`.
    Then, enable casting by removing the line in config/config.yaml that says `cast: null`.

## Cloud
The repo provides terraform to host your own Mink services in Google Cloud. The terraform defines the necessary Cloud SQL instance and supplementary resources to store the Mink container in Artifact Registry and deploy it in Cloud Run. To deploy your resources:

1. Go to GCP and create a new project
1. Configure terraform/terraform.tfvars with the appropriate values. Note: `db_password` can be anything.
1. `terraform apply`


## MCP Setup
https://docs.cloud.google.com/sql/docs/mysql/pre-built-tools-with-mcp-toolbox