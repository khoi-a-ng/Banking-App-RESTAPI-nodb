"""Tests for JWT authentication.

These describe how the API should behave once it issues JSON Web Tokens
instead of DRF's database-backed tokens. Written before the implementation,
so they fail first.

The big conceptual difference to keep in mind while reading:

  - The old DRF token was a random string that meant nothing on its own. The
    server looked it up in the `authtoken_token` table on every request.
  - A JWT carries its claims *inside itself* ({"user_id": 4, "exp": ...})
    and is signed with SECRET_KEY. The server verifies the signature with
    maths, not a database lookup.

That difference is what most of these tests are pinning down.
"""

import base64
import json
from datetime import timedelta

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from banking.tests.base import BankingAPITestCase


def decode_payload(jwt_string):
    """Pull the claims out of a JWT without verifying the signature.

    A JWT is three base64 chunks joined by dots: header.payload.signature.
    Only the signature is secret-dependent -- the payload is *not* encrypted,
    just encoded, so anyone holding the token can read what's inside it. That
    is worth seeing for yourself, which is why this helper exists.
    """
    payload = jwt_string.split(".")[1]
    # base64 needs the length to be a multiple of 4; JWTs strip the padding.
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


class JwtSignupTests(BankingAPITestCase):
    def test_signup_returns_an_access_and_refresh_token(self):
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {"name": "Jane Doe", "email": "jwt-jane@example.com", "password": "hunter2pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        # Two tokens now, not one.
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(body["customer"]["name"], "Jane Doe")

    def test_the_access_token_is_a_real_jwt(self):
        client = APIClient()
        response = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-bob@example.com", "password": "hunter2pass"},
            format="json",
        )

        access = response.json()["access"]

        # header.payload.signature
        self.assertEqual(len(access.split(".")), 3)

        claims = decode_payload(access)
        user = User.objects.get(username="jwt-bob@example.com")
        # simplejwt writes user_id as a string, not a number -- ids are not
        # always integers (UUID primary keys are common), so it stringifies
        # them for consistency. Worth knowing before you compare it to a pk.
        self.assertEqual(claims["user_id"], str(user.id))
        self.assertEqual(claims["token_type"], "access")
        self.assertIn("exp", claims)  # JWTs always carry their own expiry


class JwtLoginTests(BankingAPITestCase):
    def test_login_returns_both_tokens(self):
        client = APIClient()
        client.post(
            "/api/auth/signup/",
            {"name": "Nina L", "email": "jwt-nina@example.com", "password": "hunter2pass"},
            format="json",
        )

        response = client.post(
            "/api/auth/login/",
            {"email": "jwt-nina@example.com", "password": "hunter2pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_wrong_password_returns_no_tokens(self):
        client = APIClient()
        client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-wrong@example.com", "password": "hunter2pass"},
            format="json",
        )

        response = client.post(
            "/api/auth/login/",
            {"email": "jwt-wrong@example.com", "password": "nope-wrong-pass"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")
        self.assertNotIn("access", response.json())


class BearerSchemeTests(BankingAPITestCase):
    """JWT uses `Authorization: Bearer <token>`, not `Token <key>`."""

    def test_bearer_scheme_authenticates(self):
        client = APIClient()
        access = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-bearer@example.com", "password": "hunter2pass"},
            format="json",
        ).json()["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        self.assertEqual(client.get("/api/accounts/").status_code, 200)

    def test_the_old_token_scheme_no_longer_works(self):
        """Proof the swap actually happened -- `Token <key>` is dead."""
        client = APIClient()
        access = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-oldscheme@example.com", "password": "hunter2pass"},
            format="json",
        ).json()["access"]

        # Same valid token, wrong scheme.
        client.credentials(HTTP_AUTHORIZATION=f"Token {access}")

        self.assertEqual(client.get("/api/accounts/").status_code, 401)

    def test_a_tampered_token_is_rejected(self):
        """Flip one character of the payload and the signature stops matching.

        This is the whole security model: the claims are readable by anyone,
        but they cannot be *changed* without SECRET_KEY.
        """
        client = APIClient()
        access = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-tamper@example.com", "password": "hunter2pass"},
            format="json",
        ).json()["access"]

        header, payload, signature = access.split(".")
        tampered = f"{header}.{payload[:-4]}XXXX.{signature}"
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")

        self.assertEqual(client.get("/api/accounts/").status_code, 401)

    def test_an_expired_access_token_is_rejected(self):
        from rest_framework_simplejwt.tokens import AccessToken

        user = User.objects.create_user(
            username="expired@example.com", email="expired@example.com", password="hunter2pass"
        )
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=timedelta(seconds=-10))  # expired 10s ago

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(client.get("/api/accounts/").status_code, 401)


class JwtRefreshTests(BankingAPITestCase):
    """The refresh token's only job: buy a new access token without making
    the user type their password again."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        body = self.client.post(
            "/api/auth/signup/",
            {"name": "Nina L", "email": "jwt-refresh@example.com", "password": "hunter2pass"},
            format="json",
        ).json()
        self.access = body["access"]
        self.refresh = body["refresh"]

    def test_refresh_returns_a_new_access_token(self):
        response = self.client.post(
            "/api/auth/refresh/", {"refresh": self.refresh}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.content)
        new_access = response.json()["access"]
        self.assertNotEqual(new_access, self.access)

        # And the new one actually works.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        self.assertEqual(self.client.get("/api/accounts/").status_code, 200)

    def test_refresh_requires_a_valid_refresh_token(self):
        response = self.client.post(
            "/api/auth/refresh/", {"refresh": "not-a-real-token"}, format="json"
        )

        self.assertEqual(response.status_code, 401, response.content)

    def test_an_access_token_cannot_be_used_to_refresh(self):
        """The two token types are not interchangeable."""
        response = self.client.post(
            "/api/auth/refresh/", {"refresh": self.access}, format="json"
        )

        self.assertEqual(response.status_code, 401, response.content)


class JwtLogoutTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        body = self.client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "jwt-logout@example.com", "password": "hunter2pass"},
            format="json",
        ).json()
        self.access = body["access"]
        self.refresh = body["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_logout_blacklists_the_refresh_token(self):
        response = self.client.post(
            "/api/auth/logout/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(response.status_code, 204, response.content)

        # The refresh token is now dead -- it can't buy any more access tokens.
        again = self.client.post(
            "/api/auth/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(again.status_code, 401, again.content)

    def test_logout_without_a_refresh_token_is_rejected(self):
        response = self.client.post("/api/auth/logout/", {}, format="json")

        self.assertErrorCode(response, 400, "validation_error")

    def test_the_existing_access_token_still_works_after_logout(self):
        """This is the honest, uncomfortable part of JWT.

        Blacklisting kills the *refresh* token. It cannot kill an access
        token that is already out in the wild, because the server does not
        store access tokens anywhere -- it just checks the signature and the
        expiry baked into them. So a stolen access token stays valid until it
        expires on its own.

        That is a real downgrade from the old DRF tokens, where deleting the
        row logged you out everywhere instantly. It is the trade JWT makes,
        and the reason ACCESS_TOKEN_LIFETIME is kept short.
        """
        self.client.post("/api/auth/logout/", {"refresh": self.refresh}, format="json")

        # Still 200, not 401. Documenting reality, not wishing it away.
        self.assertEqual(self.client.get("/api/accounts/").status_code, 200)
