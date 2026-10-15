from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
def test_api_docs_accessible_by_admin(admin_user):
    client = APIClient()
    token = str(RefreshToken.for_user(admin_user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    url = reverse("api-docs")
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_api_docs_not_accessible_by_anonymous_users(client):
    url = reverse("api-docs")
    response = client.get(url)
    assert response.status_code in [HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED]


@pytest.mark.django_db
def test_api_schema_generated_successfully(admin_user):
    client = APIClient()
    token = str(RefreshToken.for_user(admin_user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    url = reverse("api-schema")
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK

