# Applications API

**Base URL:** `http://127.0.0.1:8000`

## Summary

The Applications API covers:

* Seeker job application submissions, history, and withdrawals
* Employer views of applications submitted to their jobs
* Employer status updates for candidate applications

---

## Apply to a Job

`POST /api/jobs/<job_id>/apply/`

Create a new application for an open, publicly visible job.

**Authentication**

* Requires a valid authenticated seeker
* The seeker is derived from `request.user`
* The client does not send a seeker identifier

**Rules**

* The job must be `OPEN`
* The job must belong to an approved employer
* A seeker can apply to the same job only once

**Request body**

```json
{
  "cover_letter": "I would love to work on this team.",
  "resume_id": 1
}
```

* `cover_letter` *(optional)*: Text cover letter.
* `resume_id` *(optional)*: ID of one of the seeker's uploaded resumes.

---

## List My Applications (Seeker)

`GET /api/seeker/applications/`

Return all applications submitted by the authenticated job seeker.

**Authentication**

* Header: `Authorization: Bearer <SEEKER_ACCESS_TOKEN>`
* Requires a valid authenticated seeker.

**Response example (`200 OK`)**

```json
[
  {
    "id": 1,
    "job": {
      "id": 10,
      "title": "Backend Engineer",
      "description": "API development...",
      "location": "Remote",
      "employment_type": "FULL_TIME",
      "salary_min": "80000.00",
      "salary_max": "120000.00",
      "salary_currency": "USD",
      "status": "OPEN",
      "employer": {
        "id": 2,
        "company_name": "Acme Corp",
        "website": "https://acme.com",
        "description": "Software company"
      },
      "created_at": "2026-08-17T10:00:00Z",
      "updated_at": "2026-08-17T10:00:00Z"
    },
    "seeker": {
      "id": 5,
      "user_email": "john@example.com",
      "user_name": "John Doe",
      "phone": "+1234567890",
      "bio": "Django Developer",
      "created_at": "2026-08-17T09:00:00Z",
      "updated_at": "2026-08-17T09:00:00Z"
    },
    "resume": {
      "id": 1,
      "title": "Backend Developer Resume",
      "file": "/media/resumes/2026/08/backend.pdf",
      "file_url": "http://127.0.0.1:8000/media/resumes/2026/08/backend.pdf",
      "created_at": "2026-08-17T10:00:00Z",
      "updated_at": "2026-08-17T10:00:00Z"
    },
    "cover_letter": "I would love to work on this team.",
    "status": "SUBMITTED",
    "created_at": "2026-08-17T12:00:00Z",
    "updated_at": "2026-08-17T12:00:00Z"
  }
]
```


---

## View My Application Detail (Seeker)

`GET /api/seeker/applications/<id>/`

Retrieve the details and current status of a specific application submitted by the authenticated job seeker.

**Authentication**

* Header: `Authorization: Bearer <SEEKER_ACCESS_TOKEN>`

---

## Withdraw My Application (Seeker)

`DELETE /api/seeker/applications/<id>/`

Withdraw (delete) a submitted job application.

**Authentication**

* Header: `Authorization: Bearer <SEEKER_ACCESS_TOKEN>`
* Can only delete applications owned by the authenticated seeker.

**Response**

* `204 No Content`

---

## View Applications for a Job (Employer)

`GET /api/jobs/<job_id>/applications/`

Return all applications for a specific job.

**Authentication**

* Requires a valid authenticated employer
* Only the employer who owns the job may access this endpoint

---

## View All Applications for My Jobs (Employer)

`GET /api/employer/applications/`

Return all applications submitted to jobs owned by the authenticated employer.

**Authentication**

* Requires a valid authenticated employer
* The employer must be approved

---

## Update Application Status (Employer)

`PATCH /api/employer/applications/<id>/status/`

Update the status of an application submitted to a job owned by the authenticated employer.

**Authentication**

* Header: `Authorization: Bearer <EMPLOYER_ACCESS_TOKEN>`
* Requires a valid authenticated employer whose account is approved.
* Can only update applications for jobs belonging to the authenticated employer.

**Request body**

```json
{
  "status": "SHORTLISTED"
}
```

* Supported statuses: `SUBMITTED`, `UNDER_REVIEW`, `SHORTLISTED`, `REJECTED`.

**Response example (`200 OK`)**

```json
{
  "id": 1,
  "status": "SHORTLISTED",
  "created_at": "2026-08-17T18:00:00Z",
  "updated_at": "2026-08-17T18:05:00Z"
}
```

---

## Notes

* Validation is handled in the serializer and model layer.
* Duplicate applications are rejected with a unique constraint on `(job, seeker)`.


