# Talentwright API Cheatsheet

**Base URL**: `http://127.0.0.1:8000`

## Endpoints Summary

| Endpoint | Method | Auth Required | Auth Type | Description | Request Body |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/auth/register/` | `POST` | No | None | Register a new user (Employer or Seeker) | [Example 1](#1-register-employer) / [Example 2](#2-register-seeker) |
| `/api/auth/login/` | `POST` | No | None | Log in user & receive JWT access + refresh tokens | [Example 3](#3-login) |
| `/api/auth/refresh/` | `POST` | No | None | Exchange refresh token for a new access token | [Example 4](#4-refresh-token) |
| `/api/auth/logout/` | `POST` | Yes | Bearer Token | Logout user & blacklist refresh token | [Example 5](#5-logout) |
| `/api/me/` | `GET` | Yes | Bearer Token | Get current user profile details | None |
| `/api/me/` | `PATCH` | Yes | Bearer Token | Update name or profile details (Employer / Seeker) | [Example 6](#6-update-profile-employer) / [Example 7](#7-update-profile-seeker) |
| `/api/auth/admin/employers/` | `GET` | Yes | Admin Bearer | List employers (Filterable: `?status=PENDING`) | None |
| `/api/auth/admin/employers/<id>/approve/` | `PATCH` | Yes | Admin Bearer | Approve pending employer profile | None |
| `/api/auth/admin/employers/<id>/reject/` | `PATCH` | Yes | Admin Bearer | Reject pending employer profile | None |

---

## Request Body Examples

### 1. Register (EMPLOYER)
`POST /api/auth/register/`
```json
{
  "email": "company@acme.com",
  "password": "StrongPassword123!",
  "password_confirm": "StrongPassword123!",
  "name": "Acme Admin",
  "account_type": "EMPLOYER"
}
```

### 2. Register (SEEKER)
`POST /api/auth/register/`
```json
{
  "email": "john@example.com",
  "password": "StrongPassword123!",
  "password_confirm": "StrongPassword123!",
  "name": "John Doe",
  "account_type": "SEEKER"
}
```

### 3. Login
`POST /api/auth/login/`
```json
{
  "email": "company@acme.com",
  "password": "StrongPassword123!"
}
```

### 4. Refresh Token
`POST /api/auth/refresh/`
```json
{
  "refresh": "<YOUR_REFRESH_TOKEN>"
}
```

### 5. Logout
`POST /api/auth/logout/`
Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`
```json
{
  "refresh": "<YOUR_REFRESH_TOKEN>"
}
```

### 6. Update Profile (EMPLOYER)
`PATCH /api/me/`
Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`
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

### 7. Update Profile (SEEKER)
`PATCH /api/me/`
Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`
```json
{
  "name": "John Doe",
  "seeker_profile": {
    "phone": "+1234567890",
    "bio": "Experienced Backend Django Developer."
  }
}
```
