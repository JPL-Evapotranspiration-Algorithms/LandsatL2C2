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
        prompt="credentials for EROS Registration System https://ers.cr.usgs.gov/register\n" +
               "NOTE: The M2M API now uses token-based authentication. Please provide an authentication token\n" +
               "instead of a password for the most reliable access. You can generate tokens at:\n" +
               "https://ers.cr.usgs.gov/profile/access"
    )

    return credentials

def main():
    try:
        credentials = get_M2M_credentials()
        username = credentials.get("username", "N/A")
        password = credentials.get("password", "")
        token = credentials.get("token", "")

        obscured_password = '*' * len(password) if password else "Not provided"
        obscured_token = '*' * len(token) if token else "Not provided"

        print(f"Username: {username}")
        print(f"Password: {obscured_password}")
        print(f"Token: {obscured_token}")
        
        # Provide guidance on preferred authentication method
        if token:
            print("\n✓ Token-based authentication is configured (recommended)")
        elif password:
            print("\n⚠ Using password-based authentication (deprecated)")
            print("  Consider switching to token-based authentication at:")
            print("  https://ers.cr.usgs.gov/profile/access")
        else:
            print("\n⚠ No authentication credentials found")
            
    except Exception as e:
        print(f"Error verifying credentials: {e}")

if __name__ == "__main__":
    main()
