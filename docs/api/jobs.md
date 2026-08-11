# Jobs API

**Base URL**: `http://127.0.0.1:8000`

## Summary

The Jobs API currently supports job creation only. Jobs can be created only by authenticated employers whose profile has been approved.

## Authentication

- `POST /api/jobs/` requires a Bearer token.
- The authenticated user must have an `EmployerProfile`.
- The employer profile must have `verification_status=APPROVED`.

## Endpoints

### Create a job

`POST /api/jobs/`

Create a new job posting for the authenticated employer. The employer is determined from the token and cannot be provided by the client.

**Request body**

```json
{
  "title": "Backend Engineer",
  "description": "Build APIs and core platform features.",
  "location": "Remote",
  "employment_type": "FULL_TIME",
  "salary_min": "80000.00",
  "salary_max": "120000.00",
  "salary_currency": "USD"
}
```

**Validation notes**

- `title`, `description`, and `employment_type` are required.
- `employment_type` must match one of the supported choices.
- Salary values are optional, but if both are provided, `salary_min` must be less than or equal to `salary_max`.
- `status` is server-controlled and defaults to `DRAFT`.
- The client must not pass `employer` or any employer identifier.
