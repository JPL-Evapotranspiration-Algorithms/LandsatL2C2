from typing import Dict
from os.path import join, abspath, exists, expanduser
from .credentials import get_credentials

FILENAME = join(abspath(expanduser("~")), ".M2M_credentials")

def get_M2M_credentials(filename: str = FILENAME) -> Dict[str, str]:
    if filename is None or not exists(filename):
        filename = FILENAME

    credentials = get_credentials(
        filename=filename,
        displayed=["username"],
        hidden=["password", "token"],
        prompt="credentials for EROS Registration System https://ers.cr.usgs.gov/register"
    )

    return credentials

def main():
    try:
        credentials = get_M2M_credentials()
        username = credentials.get("username", "N/A")
        password = credentials.get("password", "")
        token = credentials.get("token", "")

        obscured_password = '*' * len(password)
        obscured_token = '*' * len(token)

        print(f"Username: {username}")
        print(f"Password: {obscured_password}")
        print(f"Token: {obscured_token}")
    except Exception as e:
        print(f"Error verifying credentials: {e}")

if __name__ == "__main__":
    main()
