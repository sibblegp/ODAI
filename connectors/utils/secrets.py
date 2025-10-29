import sys
from typing import Optional

# Import the Secret Manager client library.
from google.cloud import secretmanager
from google.api_core import exceptions

# def add_secret_version(
#     project_id: str, secret_id: str, payload: str
# ):
#     """
#     Adds a new version to the given secret with the provided payload.

#     Args:
#         project_id: Google Cloud project ID.
#         secret_id: ID of the secret container.
#         payload: String data for the new secret version.

#     Returns:
#         The created SecretVersion object or None if an error occurred.
#     """
#     # Create the Secret Manager client.
#     client = secretmanager.SecretManagerServiceClient()

#     # Build the resource name of the parent secret.
#     parent = client.secret_path(project_id, secret_id)

#     # Convert the string payload into a bytes. This is required by the API.
#     payload_bytes = payload.encode("UTF-8")

#     try:
#         # Add the secret version.
#         response = client.add_secret_version(
#             request={
#                 "parent": parent,
#                 "payload": {"data": payload_bytes},
#             }
#         )
#         print(f"Added secret version: {response.name}")
#         return response
#     except exceptions.NotFound:
#         print(f"Error: Secret '{secret_id}' not found in project '{project_id}'.", file=sys.stderr)
#         print("Please create the secret container first.", file=sys.stderr)
#         return None
#     except exceptions.GoogleAPICallError as e:
#         print(f"Error adding secret version: {e}", file=sys.stderr)
#         return None


def access_secret_version(
    project_id: str, secret_id: str, version_id: str = "latest"
) -> str | None:
    """
    Accesses the payload for the given secret version.

    Args:
        project_id: Google Cloud project ID.
        secret_id: ID of the secret.
        version_id: ID of the version (e.g., "latest", "5"). Defaults to "latest".

    Returns:
        The decoded secret payload as a string, or None if an error occurred.
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = client.secret_version_path(project_id, secret_id, version_id)

    try:
        # Access the secret version.
        response = client.access_secret_version(request={"name": name})

        # Decode the payload.
        payload = response.payload.data.decode("UTF-8")
        # Optional: Print metadata (useful for confirming version)
        # print(f"Accessed secret version: {response.name}")
        return payload
    except exceptions.NotFound:
        print(f"Error: Secret '{secret_id}' or version '{version_id}' not found in project '{project_id}'.", file=sys.stderr)
        return None
    except exceptions.PermissionDenied:
         print(f"Error: Permission denied accessing secret '{secret_id}' version '{version_id}'.", file=sys.stderr)
         print("Ensure the authenticated principal has the 'Secret Manager Secret Accessor' role.", file=sys.stderr)
         return None
    except exceptions.GoogleAPICallError as e:
        print(f"Error accessing secret version: {e}", file=sys.stderr)
        return None