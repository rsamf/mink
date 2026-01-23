import argparse
import os
import sys
import requests


def main():
    parser = argparse.ArgumentParser(description="Mink CLI Tool")
    parser.add_argument("api_key", help="API Key for authentication")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument(
        "--url", default="http://localhost:8000/take-notes", help="Service URL"
    )

    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: File '{args.video_path}' not found.")
        sys.exit(1)

    headers = {"X-API-Key": args.api_key}

    print(f"Sending '{args.video_path}' to {args.url}...")

    try:
        with open(args.video_path, "rb") as f:
            files = {"file": f}
            response = requests.post(args.url, headers=headers, files=files)

        print(f"Status Code: {response.status_code}")
        try:
            print("Response:", response.json())
        except requests.exceptions.JSONDecodeError:
            print("Response Text:", response.text)

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {args.url}. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
