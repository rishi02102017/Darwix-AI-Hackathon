import requests

url = "http://127.0.0.1:8000/transcribe/"


# Change filename to match one of yours
file_path = "OSR_us_000_0013_8k.wav"

with open(file_path, 'rb') as audio_file:
    files = {'audio': audio_file}
    response = requests.post(url, files=files)

print("Status Code:", response.status_code)
print("Response:")
print(response.json())
