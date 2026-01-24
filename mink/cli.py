import argparse
import os
import sys
import requests
import time
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.layout import Layout


console = Console()

HELP = \
"""
This Mink CLI allows you to submit recorded meetings for AI textual extraction and notetaking.
You can also view historical meetings and jobs. Whenever you submit a video, a meeting
and a job will be constructed for AI extraction will be created for the video.

Warning: Mink doesn't support user authorization (yet), and all extracted information from video
recordings will be made public. Here, public is defined as accessible by anyone using the deployed
demo service and holding a valid API key for the service.

I will only distribute API keys to Roboflow team members (and myself).
"""

def main():
    parser = argparse.ArgumentParser(prog="mink", description=HELP)
    # Global arguments
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Service Base URL"
    )
    parser.add_argument("api_key", help="API Key for authentication")
    subparser = parser.add_subparsers(dest="command")
    submit = subparser.add_parser("submit", help="Submit a video for processing")
    meeting = subparser.add_parser("meeting", help="View meeting information")
    job = subparser.add_parser("job", help="View job information")


    # Command-specific arguments
    submit.add_argument("video_path", help="Path to the video file")
    job.add_argument("job_id", help="Job ID to query")
    meeting.add_argument("meeting_id", help="Meeting ID to query")

    args = parser.parse_args()
    if args.command == "submit":
        submit_video(args)
    elif args.command == "job":
        get_job(args)
    elif args.command == "meeting":
        get_meeting(args)
    else:
        console.print(f"Invalid command {args.command}.")
        parser.print_help()


def visualize_response(response: dict):
    transcript = response.get("transcript_events", [])
    ocr = response.get("ocr_events", [])
    notes = response.get("intelligent_notes", [])

    transcript_str = "\n".join(
        [
            f"[{event['start']:.1f} - {event['end']:.1f}] {event['speaker_name']}: {event['content']}"
            for event in transcript
        ]
    )
    ocr_str = "\n".join(
        [
            f"[{event['start']:.1f} - {event['end']:.1f}] {event['content']}"
            for event in ocr
        ]
    )

    if notes:
        notes_str = "\n".join([f"{note['content']}\n\n" for note in notes])
        with console.pager():
            console.print(Markdown(notes_str))
    else:
        console.print(
            "[red](No Intelligent Notes found. It may be disabled in the server.)"
        )

    with console.pager():
        console.print(transcript_str)

    with console.pager():
        console.print(ocr_str)


def submit_video(args):
    if not os.path.exists(args.video_path):
        console.print(f"Error: File '{args.video_path}' not found.")
        sys.exit(1)

    headers = {"X-API-Key": args.api_key}
    try:
        with console.status(f"Sending '{args.video_path}' to {args.url}/take-notes..."):
            with open(args.video_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{args.url}/take-notes", headers=headers, files=files
                )

        if response.status_code != 200:
            console.print(f"Error: {response.status_code}")
            console.print(response.text)
            sys.exit(1)

        job = response.json()
        current_job_status = job["job_status"]
        job_id = job["job_id"]
        console.print(f"Submitted Job ID: [cyan]{job_id}")
        console.print(f"Created new meeting (meeting id: [cyan]{job['meeting_id']}[/cyan])")
        console.print(f"Status: [green]{current_job_status}")

        with console.status("Waiting for job to complete..."):
            while current_job_status != "completed" and current_job_status != "failed":
                time.sleep(1)
                response = requests.get(f"{args.url}/job/{job_id}", headers=headers)
                if response.status_code != 200:
                    console.print(f"Error: {response.status_code}")
                    console.print(response.text)
                    sys.exit(1)

                job = response.json()
                if current_job_status != job["job_status"]:
                    console.print(f"Status: [green]{job['job_status']}")
                    current_job_status = job["job_status"]

        if current_job_status == "completed":
            try:
                json_response = response.json()
                visualize_response(json_response)
            except requests.exceptions.JSONDecodeError:
                console.print("Response Text:", response.text)
        else:
            console.print("[red]Failed to complete job.")

    except requests.exceptions.ConnectionError:
        console.print(f"Error: Could not connect to {args.url}. Is the server running?")
        sys.exit(1)
    except Exception as e:
        console.print(f"An error occurred: {e}")
        sys.exit(1)


def get_job(args):
    headers = {"X-API-Key": args.api_key}
    response = requests.get(f"{args.url}/job/{args.job_id}", headers=headers)
    if response.status_code != 200:
        console.print(f"Error: {response.status_code}")
        console.print(response.text)
        sys.exit(1)

    job = response.json()
    visualize_response(job)
    
def get_meeting(args):
    headers = {"X-API-Key": args.api_key}
    response = requests.get(f"{args.url}/meeting/{args.meeting_id}", headers=headers)
    if response.status_code != 200:
        console.print(f"Error: {response.status_code}")
        console.print(response.text)
        sys.exit(1)

    meeting = response.json()
    jobs = meeting.get("jobs", [])
    layout = Layout()
    layout.split_column(
        Layout(name="meeting"),
        Layout(name="jobs"),
    )
    meeting_table = Table(title="Meeting Information")
    meeting_table.add_column("Meeting ID", style="cyan", no_wrap=True)
    meeting_table.add_column("Name", style="green")
    meeting_table.add_column("Time Started", style="yellow")
    meeting_table.add_column("Duration", style="yellow")
    meeting_table.add_row(
        str(meeting["id"]),
        meeting["name"],
        datetime.fromtimestamp(meeting["time_started"]).strftime("%Y-%m-%d %H:%M:%S"),
        str(meeting["duration"]),
    )
    layout["meeting"].update(meeting_table)
    
    jobs_table = Table(title="Jobs in Meeting")
    jobs_table.add_column("Job ID", style="cyan", no_wrap=True)
    jobs_table.add_column("Status", style="green")
    jobs_table.add_column("Time Started", style="yellow")
    jobs_table.add_column("No. Transcript Events", style="yellow")
    jobs_table.add_column("No. OCR Events", style="yellow")
    jobs_table.add_column("No. Intelligent Notes", style="yellow")
    for job in jobs:
        time_started = job.get("time_started")
        if time_started:
            time_started_str = datetime.fromtimestamp(time_started).strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_started_str = "[red]N/A"
        jobs_table.add_row(
            job["job_id"],
            job["job_status"],
            time_started_str,
            str(len(job.get("transcript_events", []))),
            str(len(job.get("ocr_events", []))),
            str(len(job.get("intelligent_notes", []))),
        )    
    layout["jobs"].update(jobs_table)
    console.print(layout)


if __name__ == "__main__":
    main()
