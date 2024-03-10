import requests

# PythonAnywhere API endpoint and credentials
api_endpoint = "https://www.pythonanywhere.com/api/v0/user/codingthebrains/"
api_token = "4402552c642ad666377b9364f80cd0007274d1df"
headers = {"Authorization": f"Token {api_token}"}

def send_console_command(console_id, command):
    url = f"{api_endpoint}consoles/{console_id}/send_input/"
    data = {"input": f"{command}\n"}
    response = requests.post(url, headers=headers, data=data)
    return response.ok

def reload_web_app():
    url = f"{api_endpoint}webapps/codingthebrains.pythonanywhere.com/reload/"
    response = requests.post(url, headers=headers)
    return response.ok

def main():
    console_id = 32786310
    if send_console_command(console_id, "git pull"):
        print("Git pull command sent successfully.")
    else:
        print("Failed to send git pull command.")

    if reload_web_app():
        print("Web app reloaded successfully.")
    else:
        print("Failed to reload web app.")

if __name__ == "__main__":

    main()
    pass