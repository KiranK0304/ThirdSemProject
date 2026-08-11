# Jobs API

**Base URL:** `http://127.0.0.1:8000`

## Summary

The Jobs API allows verified employers to manage their own job postings.

Currently, authenticated and approved employers can:

* Create a job
* List their own jobs
* Retrieve a specific job they own
* Update one of their jobs
* Delete one of their jobs

All operations are restricted to jobs owned by the authenticated employer.

---

## Authentication

All endpoints require a valid JWT Bearer token.

Requirements:

* The authenticated user must have an `EmployerProfile`.
* The employer's `verification_status` must be `APPROVED`.
* The authenticated employer is determined from the JWT. The client must never provide an employer identifier.

---

## Endpoints

### Create Job

`POST /api/jobs/`

Create a new job posting for the authenticated employer.

**Request Body**

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

**Validation Notes**

* `title`, `description`, and `employment_type` are required.
* `employment_type` must match one of the supported choices.
* If both salary values are provided, `salary_min` must be less than or equal to `salary_max`.
* `status` is managed by the server and cannot be supplied by the client.
* The client must not provide `employer` or any employer identifier.

---

### List My Jobs

`GET /api/jobs/`

Returns all jobs created by the authenticated employer.

**Authentication**

* Bearer Token required.
* Only approved employers may access this endpoint.

---

### Retrieve Job

`GET /api/jobs/<id>/`

Returns the details of a specific job owned by the authenticated employer.

**Authentication**

* Bearer Token required.
* The requested job must belong to the authenticated employer.
* If the job does not belong to the authenticated employer (or does not exist), an appropriate error response is returned.

---

### Update Job

`PATCH /api/jobs/<id>/`

Update one or more fields of a job owned by the authenticated employer.

**Example Request**

```json
{
  "title": "Senior Backend Engineer",
  "salary_max": "140000.00"
}
```

**Validation Notes**

* Partial updates are supported.
* Model validation is executed before saving.
* Server-managed fields (`id`, `status`, `created_at`, `updated_at`) cannot be modified.
* Ownership is verified before the update is performed.

---

### Delete Job

`DELETE /api/jobs/<id>/`

Delete a job owned by the authenticated employer.

**Authentication**

* Bearer Token required.
* Ownership is verified before deletion.
* Employers may delete only their own job postings.

---

## Authorization Rules

The Jobs API enforces the following rules:

* Only authenticated users may access these endpoints.
* Only approved employers may manage jobs.
* Employers can manage only their own job postings.
* Employer ownership is determined from the authenticated user, never from client-provided data.
* All validation is performed using the serializer and model-level validation to ensure data integrity.
