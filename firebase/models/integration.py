"""Integration model for managing ODAI integrations."""

from google.cloud.firestore_v1.base_query import FieldFilter

from ..base import FireStoreObject


class Integration(FireStoreObject):
    """Integration model for managing ODAI integrations."""

    name: str
    description: str
    prompts: list[str]

    def __init__(self, media_object) -> None:
        super().__init__()
        self.__media_object = media_object
        self.reference_id = media_object.reference.id

        for key in media_object.to_dict():
            setattr(self, key, media_object.to_dict()[key])

    @classmethod
    def create_integration(cls, internal_id: str, logo_url: str, integration_name: str, integration_description: str, prompts: list[str]):
        existing_integration = cls.find_odai_integration_by_name(
            integration_name)
        if existing_integration:
            existing_integration.prompts = prompts
            existing_integration.description = integration_description
            cls.odai_integrations.document(existing_integration.reference_id).update({
                'prompts': existing_integration.prompts,
                'description': existing_integration.description,
                'logo_url': logo_url,
                'internal_id': internal_id
            })
            return existing_integration
        else:
            new_integration = cls.odai_integrations.document().set({
                'name': integration_name,
                'description': integration_description,
                'prompts': prompts,
                'logo_url': logo_url,
                'internal_id': internal_id
            })
            new_integration = cls.find_odai_integration_by_name(
                integration_name)
            return new_integration

    @classmethod
    def find_odai_integration_by_name(cls, integration_name: str) -> 'Integration | None':
        integration = cls.odai_integrations.where(
            filter=FieldFilter('name', '==', integration_name)).get()
        if len(integration) > 0:
            return cls(integration[0])
        else:
            return None
