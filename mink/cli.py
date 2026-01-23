import requests

test_video = "test.mp4"

response = requests.post(
    "http://localhost:8000/take-notes", files={"file": open(test_video, "rb")}
)
print(response.json())
