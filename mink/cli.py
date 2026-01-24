import argparse
import os
import sys
import requests
import time


def main():
    parser = argparse.ArgumentParser(description="Mink CLI Tool")
    parser.add_argument("api_key", help="API Key for authentication")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Service Base URL"
    )

    args = parser.parse_args()
    if not os.path.exists(args.video_path):
        print(f"Error: File '{args.video_path}' not found.")
        sys.exit(1)

    headers = {"X-API-Key": args.api_key}

    print(f"Sending '{args.video_path}' to {args.url}/take-notes...")

    try:
        with open(args.video_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{args.url}/take-notes", headers=headers, files=files
            )

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            sys.exit(1)

        job = response.json()
        current_job_status = job["job_status"]
        job_id = job["job_id"]
        print(f"Submitted Job ID: {job_id}")
        print(f"Status: {current_job_status}")

        while current_job_status != "completed" and current_job_status != "failed":
            time.sleep(1)
            response = requests.get(f"{args.url}/job/{job_id}", headers=headers)
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(response.text)
                sys.exit(1)

            job = response.json()
            if current_job_status != job["job_status"]:
                print(f"Status: {job['job_status']}")
                current_job_status = job["job_status"]

        if current_job_status == "completed":
            try:
                print("Response:", response.json())
            except requests.exceptions.JSONDecodeError:
                print("Response Text:", response.text)
        else:
            print("Failed to complete job.")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {args.url}. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
