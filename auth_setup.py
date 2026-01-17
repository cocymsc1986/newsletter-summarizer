import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# We only need read-only access to fetch the newsletters
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def generate_token():
    # Load the credentials you just downloaded
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    # This opens your browser for a one-time login
    creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
    
    # Save the token to a file
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\nSuccess! 'token.json' has been created.")
    print("Now run the following command to get your GitHub Secret string:")
    print("cat token.json | base64 | pbcopy  # (on Mac) or 'base64 token.json' on Linux")

if __name__ == "__main__":
    generate_token()
