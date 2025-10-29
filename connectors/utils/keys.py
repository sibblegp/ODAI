import datetime

from google.cloud import kms
from google.cloud import kms
from google.protobuf import duration_pb2  # type: ignore

def create_key_hsm(
    project_id: str, location_id: str, key_ring_id: str, key_id: str
) -> kms.CryptoKey:
    """
    Creates a new key in Cloud KMS backed by Cloud HSM.

    Args:
        project_id (string): Google Cloud project ID (e.g. 'my-project').
        location_id (string): Cloud KMS location (e.g. 'us-east1').
        key_ring_id (string): ID of the Cloud KMS key ring (e.g. 'my-key-ring').
        key_id (string): ID of the key to create (e.g. 'my-hsm-key').

    Returns:
        CryptoKey: Cloud KMS key.

    """

    # Create the client.
    client = kms.KeyManagementServiceClient()

    # Build the parent key ring name.
    key_ring_name = client.key_ring_path(project_id, location_id, key_ring_id)

    # Build the key.
    purpose = kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT
    algorithm = (
        kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
    )
    protection_level = kms.ProtectionLevel.SOFTWARE
    key = {
        "purpose": purpose,
        "version_template": {
            "algorithm": algorithm,
            "protection_level": protection_level,
        },
        # Optional: customize how long key versions should be kept before
        # destroying.
        "destroy_scheduled_duration": duration_pb2.Duration().FromTimedelta(
            datetime.timedelta(days=1)
        ),
    }

    # Call the API.
    created_key = client.create_crypto_key(
        request={"parent": key_ring_name, "crypto_key_id": key_id, "crypto_key": key}
    )
    print(f"Created hsm key: {created_key.name}")
    return created_key


def encrypt_symmetric(
    project_id: str, location_id: str, key_ring_id: str, key_id: str, plaintext: str
) -> kms.EncryptResponse:
    """
    Encrypt plaintext using a symmetric key.

    Args:
        project_id (string): Google Cloud project ID (e.g. 'my-project').
        location_id (string): Cloud KMS location (e.g. 'us-east1').
        key_ring_id (string): ID of the Cloud KMS key ring (e.g. 'my-key-ring').
        key_id (string): ID of the key to use (e.g. 'my-key').
        plaintext (string): message to encrypt

    Returns:
        bytes: Encrypted ciphertext.

    """

    # Convert the plaintext to bytes.
    plaintext_bytes = plaintext.encode("utf-8")

    # Optional, but recommended: compute plaintext's CRC32C.
    # See crc32c() function defined below.
    plaintext_crc32c = crc32c(plaintext_bytes)

    # Create the client.
    client = kms.KeyManagementServiceClient()

    # Build the key name.
    key_name = client.crypto_key_path(project_id, location_id, key_ring_id, key_id)

    # Call the API.
    encrypt_response = client.encrypt(
        request={
            "name": key_name,
            "plaintext": plaintext_bytes,
            "plaintext_crc32c": plaintext_crc32c,
        }
    )

    # Optional, but recommended: perform integrity verification on encrypt_response.
    # For more details on ensuring E2E in-transit integrity to and from Cloud KMS visit:
    # https://cloud.google.com/kms/docs/data-integrity-guidelines
    if not encrypt_response.verified_plaintext_crc32c:
        raise Exception("The request sent to the server was corrupted in-transit.")
    if not encrypt_response.ciphertext_crc32c == crc32c(encrypt_response.ciphertext):
        raise Exception(
            "The response received from the server was corrupted in-transit."
        )
    # End integrity verification

    #print(f"Ciphertext: {base64.b64encode(encrypt_response.ciphertext)}")
    return encrypt_response



def decrypt_symmetric(
    project_id: str, location_id: str, key_ring_id: str, key_id: str, ciphertext: bytes
) -> kms.DecryptResponse:
    """
    Decrypt the ciphertext using the symmetric key

    Args:
        project_id (string): Google Cloud project ID (e.g. 'my-project').
        location_id (string): Cloud KMS location (e.g. 'us-east1').
        key_ring_id (string): ID of the Cloud KMS key ring (e.g. 'my-key-ring').
        key_id (string): ID of the key to use (e.g. 'my-key').
        ciphertext (bytes): Encrypted bytes to decrypt.

    Returns:
        DecryptResponse: Response including plaintext.

    """

    # Create the client.
    client = kms.KeyManagementServiceClient()

    # Build the key name.
    key_name = client.crypto_key_path(project_id, location_id, key_ring_id, key_id)

    # Optional, but recommended: compute ciphertext's CRC32C.
    # See crc32c() function defined below.
    ciphertext_crc32c = crc32c(ciphertext)

    # Call the API.
    decrypt_response = client.decrypt(
        request={
            "name": key_name,
            "ciphertext": ciphertext,
            "ciphertext_crc32c": ciphertext_crc32c,
        }
    )

    # Optional, but recommended: perform integrity verification on decrypt_response.
    # For more details on ensuring E2E in-transit integrity to and from Cloud KMS visit:
    # https://cloud.google.com/kms/docs/data-integrity-guidelines
    if not decrypt_response.plaintext_crc32c == crc32c(decrypt_response.plaintext):
        raise Exception(
            "The response received from the server was corrupted in-transit."
        )
    # End integrity verification

    #print(f"Plaintext: {decrypt_response.plaintext!r}")
    return decrypt_response


def crc32c(data: bytes) -> int:
    """
    Calculates the CRC32C checksum of the provided data.
    Args:
        data: the bytes over which the checksum should be calculated.
    Returns:
        An int representing the CRC32C checksum of the provided bytes.
    """
    import crcmod  # type: ignore

    crc32c_fun = crcmod.predefined.mkPredefinedCrcFun("crc-32c")
    return crc32c_fun(data)
