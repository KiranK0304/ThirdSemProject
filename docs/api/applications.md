# Applications API

**Base URL:** `http://127.0.0.1:8000`

## Summary

The Applications API covers:

* Seeker job applications
* Employer views of applications submitted to their jobs

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
  "cover_letter": "I would love to work on this team."
}
```

The `cover_letter` field is optional.

---

## View Applications for a Job

`GET /api/jobs/<job_id>/applications/`

Return all applications for a specific job.

**Authentication**

* Requires a valid authenticated employer
* Only the employer who owns the job may access this endpoint

---

## View All Applications for My Jobs

`GET /api/employer/applications/`

Return all applications submitted to jobs owned by the authenticated employer.

**Authentication**

* Requires a valid authenticated employer
* The employer must be approved

---

## Notes

* Validation is handled in the serializer and model layer.
* Duplicate applications are rejected with a unique constraint on `(job, seeker)`.
