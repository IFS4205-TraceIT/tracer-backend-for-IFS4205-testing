from django.conf import settings

import hvac
import requests 

def create_vault_client() -> hvac.Client:
    """
    Instantiates a hvac / vault client.
    :return: hvac.Client
    """
    vault_client = hvac.Client(**settings.VAULT_SETTINGS)

    if 'certs' in settings.VAULT_SETTINGS and settings.VAULT_SETTINGS.certs:
        # When use a self-signed certificate for the vault service itself, we need to
        # include our local ca bundle here for the underlying requests module.
        rs = requests.Session()
        vault_client.session = rs
        rs.verify = settings.VAULT_SETTINGS.certs

    # vault_client.token = _load_vault_token(vault_client)

    if not vault_client.is_authenticated():
            error_msg = 'Unable to authenticate to the Vault service'
            raise hvac.exceptions.Unauthorized(error_msg)

    return vault_client
