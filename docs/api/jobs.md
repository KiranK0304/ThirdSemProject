# Jobs API

**Base URL:** `http://127.0.0.1:8000`

## Summary

The Jobs API is split into two parts:

* Public read endpoints for job search and discovery.
* Authenticated employer-management endpoints for creating and maintaining jobs.

Public endpoints only expose jobs that are:

* `OPEN`
* posted by an employer whose verification status is `APPROVED`

Sensitive ownership data is not exposed in the public responses.

---

## Public Job Search

These endpoints are accessible to everyone.

### List Open Jobs (with Search & Filtering)

`GET /api/jobs/`

Return all jobs that are currently open and belong to approved employers.

**Supported Query Parameters**

| Parameter | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `search` | string | `?search=python` | Searches across `title`, `description`, `location`, and employer `company_name`. |
| `employment_type` | string | `?employment_type=FULL_TIME` | Filters by type: `FULL_TIME`, `PART_TIME`, `CONTRACT`, `INTERNSHIP`, `TEMPORARY`, `FREELANCE`. |
| `location` | string | `?location=Remote` | Filters jobs by location string (case-insensitive contains). |
| `min_salary` | number | `?min_salary=80000` | Filters jobs with maximum salary greater than or equal to this amount. |
| `ordering` | string | `?ordering=-created_at` | Sort results. Options: `created_at`, `-created_at`, `salary_min`, `-salary_min`, `salary_max`, `-salary_max`, `title`. |

**Rules**

* Only jobs with `status = OPEN` are returned.
* Only jobs from employers with `verification_status = APPROVED` are returned.
* Closed, draft, archived, or pending-employer jobs are excluded.

### View Open Job Details


`GET /api/jobs/<id>/`

Return the details of a single open job from an approved employer.

**Rules**

* The job must be `OPEN`.
* The employer must be approved.
* If the job is not public, the API returns `404`.

**Public response includes**

* Job title and description
* Location
* Employment type
* Salary range
* Employer company information such as company name and website

**Public response excludes**

* Employer ownership references
* Internal user or employer profile identifiers beyond the job identifier needed for the endpoint
* Any private admin or management-only fields

---

## Employer Job Management

These endpoints require a valid JWT Bearer token and an approved employer account.

### Create Job

`POST /api/jobs/manage/`

Create a new job posting for the authenticated employer.

**Authentication**

* Header: `Authorization: Bearer <YOUR_ACCESS_TOKEN>`
* The user must have an `EmployerProfile`
* The employer must be approved

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

* `title`, `description`, and `employment_type` are required.
* `employment_type` must match one of the supported choices.
* If both salary values are provided, `salary_min` must be less than or equal to `salary_max`.
* `status` is managed by the server and cannot be supplied by the client.

### List My Jobs

`GET /api/jobs/manage/`

Return all jobs created by the authenticated employer.

**Supported Query Parameters**

| Parameter | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `status` | string | `?status=DRAFT` | Filters jobs by status (`DRAFT`, `OPEN`, `CLOSED`, `ARCHIVED`). |
| `search` | string | `?search=backend` | Searches employer's jobs by title, description, or location. |
| `ordering` | string | `?ordering=-created_at` | Sorts employer's jobs. |

### Retrieve My Job


`GET /api/jobs/manage/<id>/`

Return a specific job owned by the authenticated employer.

### Update My Job

`PATCH /api/jobs/manage/<id>/`

Update one or more fields of a job owned by the authenticated employer.

**Example request**

```json
{
  "title": "Senior Backend Engineer",
  "salary_max": "140000.00"
}
```

### Delete My Job

`DELETE /api/jobs/manage/<id>/`

Delete a job owned by the authenticated employer.

---

## Authorization Rules

* Public read endpoints are available without authentication.
* Employer-management endpoints require authentication.
* Only approved employers may create, update, or delete jobs.
* Employers can manage only their own job postings.
* Public search never exposes jobs that are not `OPEN` or not posted by approved employers.

## Related Endpoints

Job application endpoints live in [applications.md](applications.md) and are mounted under the job URL space:

* `POST /api/jobs/<job_id>/apply/`
* `GET /api/jobs/<job_id>/applications/`
* `GET /api/employer/applications/`
