# Users API

**Base URL**: `http://127.0.0.1:8000`

## Summary

The Users API covers authentication, the current user profile, and admin employer approval workflows.

## Authentication

- `POST /api/auth/register/` - no authentication required.
- `POST /api/auth/login/` - no authentication required.
- `POST /api/auth/refresh/` - no authentication required.
- `POST /api/auth/logout/` - requires a Bearer token.
- `GET /api/me/` - requires a Bearer token.
- `PATCH /api/me/` - requires a Bearer token.
- Admin employer endpoints require a Bearer token for an admin user.

## Endpoints

### Register a user

`POST /api/auth/register/`

Register a new user as either an employer or seeker. The API creates the corresponding profile automatically.

**Request body**

```json
{
  "email": "company@acme.com",
  "password": "StrongPassword123!",
  "password_confirm": "StrongPassword123!",
  "name": "Acme Admin",
  "account_type": "EMPLOYER"
}
```

### Log in

`POST /api/auth/login/`

Log in with email and password and receive JWT access and refresh tokens.

**Request body**

```json
{
  "email": "company@acme.com",
  "password": "StrongPassword123!"
}
```

### Refresh token

`POST /api/auth/refresh/`

Exchange a refresh token for a new access token.

**Request body**

```json
{
  "refresh": "<YOUR_REFRESH_TOKEN>"
}
```

### Log out

`POST /api/auth/logout/`

Blacklist a refresh token and end the session.

**Authentication**

- Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`

**Request body**

```json
{
  "refresh": "<YOUR_REFRESH_TOKEN>"
}
```

### Current user profile

`GET /api/me/`

Return the authenticated user's profile details.

**Authentication**

- Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`

### Update current user profile

`PATCH /api/me/`

Update the authenticated user's name and nested employer or seeker profile data.

**Authentication**

- Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`

**Employer request body example**

```json
{
  "name": "Acme Hiring Team",
  "employer_profile": {
    "company_name": "Acme Corporation",
    "website": "https://acme.com",
    "description": "Innovative software solutions."
  }
}
```

**Seeker request body example**

```json
{
  "name": "John Doe",
  "seeker_profile": {
    "phone": "+1234567890",
    "bio": "Experienced Backend Django Developer."
  }
}
```

### List employer profiles for admins

`GET /api/auth/admin/employers/`

List employer profiles for admin review. Optional filter: `?status=PENDING`.

**Authentication**

- Header: `Authorization: Bearer <ADMIN_ACCESS_TOKEN>`

### Approve an employer profile

`PATCH /api/auth/admin/employers/<id>/approve/`

Approve an employer profile and mark it as verified.

**Authentication**

- Header: `Authorization: Bearer <ADMIN_ACCESS_TOKEN>`

### Reject an employer profile

`PATCH /api/auth/admin/employers/<id>/reject/`

Reject an employer profile.

**Authentication**

- Header: `Authorization: Bearer <ADMIN_ACCESS_TOKEN>`
