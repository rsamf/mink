<p align="center">
  <img src="assets/logo.png" alt="Logo" width=256>
  <p align="center">
    <sup>Image generated with Nano Banana Pro</sup>
  </p>

  <h1 align="center">Mink</h1>

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

## Deploy Your Own Mink

### Cloud
The repo provides terraform to host your own Mink services in Google Cloud. The terraform defines the necessary Cloud SQL instance and supplementary resources to store the Mink container in Artifact Registry and deploy it in Cloud Run. To deploy your resources:

1. Go to GCP and create a new project
1. Configure terraform/terraform.tfvars with the appropriate values. Note: `db_password` can be anything.
1. Run `terraform apply` inside of terraform.

Note: The Cloud Run service will timeout because your container image isn't in Artifact Registry yet. This is fine.

## Config
Mink uses [hydra](https://hydra.cc/docs/intro/) for flexible configuration of the server.
The available configuration can be used, but it needs two extra entries to get it working:

1.
    For demo purposes, the server has a simple mechanism to restrict access to people that are "invited"
    with an API key. You can write your own api keys (e.g. "password123") into `server.auth.keys` in config/config.yaml.
    Be creative and supply it with 1 or more API keys.

1.
    The container that is running locally will consume config/db/localconn.yaml, but the one deployed in Cloud Run will use config/db/cloudsql.yaml which will point to the correct environment variables, so don't change that file. To provide localconn.yaml the correct connection info, go to the terraform directory, and run `terraform output`.

1. 
    (Optional) You may provide an Anthropic API key to gather meeting insights (i.e. "casting" raw text data to valuable insights). Only Anthropic is supported right now.
    Please, add one in config/cast/anthropic.yaml at `api_key`.
    Then, enable casting by removing the line in config/config.yaml that says `cast: null`.

## Build the Docker Image

Once configured,

1. Build the image:
    ```bash
    docker build -t mink .
    ```
    With LightOnOCR support:

    ```bash
    docker build --build-arg sync_options="--all-extras" -t mink .
    ```
2. Run it locally:
    ```bash
    docker run --rm -d -p 8000:8000 mink
    ```
    *Or*, tag and push it to your artifact registry:
    ```bash
    docker tag mink <artifact_registry_url>
    docker push <artifact_registry_url>
    ```

## Or run without Docker

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

> [!TIP]
> You may get a connection error if you haven't deployed Cloud SQL yet since Mink depends on that to store its data.


## MCP Setup (Optional)
For more advanced usage of Mink, you can integrate it with existing agent platforms such as Claude Desktop. This allows you to conversationally use Mink for viewing meeting information, get even more personalized insights about past meetings, and perform other actions given the meeting information.

1. First, install Google's MCP Toolbox:
https://docs.cloud.google.com/sql/docs/mysql/pre-built-tools-with-mcp-toolbox#install-the-mcp-toolbox
1. Then, configure your choice of LLM system:
https://docs.cloud.google.com/sql/docs/mysql/pre-built-tools-with-mcp-toolbox#configure-the-mcp-client