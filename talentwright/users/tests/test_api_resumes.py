import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.users.models import Resume, SeekerProfile, User

pytestmark = pytest.mark.django_db


class TestSeekerResumeAPI:
    def setup_method(self):
        self.client = APIClient()

    def _login_seeker(self, email: str = "seeker-resume@example.com") -> tuple[User, SeekerProfile]:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            name="Resume Candidate",
            is_active=True,
        )
        seeker = SeekerProfile.objects.create(user=user, phone="+1234567890", bio="Bio info")
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        return user, seeker

    def test_seeker_can_upload_resume(self):
        _, seeker = self._login_seeker()
        fake_pdf = SimpleUploadedFile("my_resume.pdf", b"%PDF-1.4 dummy pdf content", content_type="application/pdf")

        response = self.client.post(
            reverse("auth_api:seeker-resumes"),
            {"title": "Software Engineer Resume", "file": fake_pdf},
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Software Engineer Resume"
        assert "file_url" in response.data
        assert Resume.objects.filter(seeker=seeker).count() == 1

    def test_seeker_cannot_upload_more_than_three_resumes(self):
        _, seeker = self._login_seeker()

        for i in range(1, 4):
            pdf_file = SimpleUploadedFile(f"resume_{i}.pdf", b"%PDF-1.4 content", content_type="application/pdf")
            resp = self.client.post(
                reverse("auth_api:seeker-resumes"),
                {"title": f"Resume {i}", "file": pdf_file},
                format="multipart",
            )
            assert resp.status_code == status.HTTP_201_CREATED

        assert Resume.objects.filter(seeker=seeker).count() == 3

        # Attempt 4th upload
        fourth_pdf = SimpleUploadedFile("resume_4.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        fourth_resp = self.client.post(
            reverse("auth_api:seeker-resumes"),
            {"title": "Resume 4", "file": fourth_pdf},
            format="multipart",
        )

        assert fourth_resp.status_code == status.HTTP_400_BAD_REQUEST
        assert Resume.objects.filter(seeker=seeker).count() == 3

    def test_seeker_can_delete_resume_and_upload_again(self):
        _, seeker = self._login_seeker()

        created_resumes = []
        for i in range(1, 4):
            pdf_file = SimpleUploadedFile(f"resume_{i}.pdf", b"%PDF-1.4 content", content_type="application/pdf")
            resp = self.client.post(
                reverse("auth_api:seeker-resumes"),
                {"title": f"Resume {i}", "file": pdf_file},
                format="multipart",
            )
            created_resumes.append(resp.data["id"])

        # Delete one resume
        delete_resp = self.client.delete(
            reverse("auth_api:seeker-resume-detail", kwargs={"pk": created_resumes[0]})
        )
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT
        assert Resume.objects.filter(seeker=seeker).count() == 2

        # Can now upload again
        new_pdf = SimpleUploadedFile("resume_new.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        new_resp = self.client.post(
            reverse("auth_api:seeker-resumes"),
            {"title": "New Resume", "file": new_pdf},
            format="multipart",
        )
        assert new_resp.status_code == status.HTTP_201_CREATED
        assert Resume.objects.filter(seeker=seeker).count() == 3

    def test_seeker_can_update_resume_title(self):
        _, seeker = self._login_seeker()
        resume = Resume.objects.create(
            seeker=seeker,
            title="Old Resume Title",
            file="resumes/2026/08/resume.pdf",
        )

        response = self.client.patch(
            reverse("auth_api:seeker-resume-detail", kwargs={"pk": resume.pk}),
            {"title": "Updated Resume Title"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        resume.refresh_from_db()
        assert resume.title == "Updated Resume Title"

    def test_invalid_file_format_rejected(self):
        self._login_seeker()
        bad_file = SimpleUploadedFile("script.py", b"print('hack')", content_type="text/x-python")

        response = self.client.post(
            reverse("auth_api:seeker-resumes"),
            {"title": "Python script", "file": bad_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data

    def test_user_me_endpoint_includes_resumes(self):
        _, seeker = self._login_seeker()
        pdf_file = SimpleUploadedFile("portfolio.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        self.client.post(
            reverse("auth_api:seeker-resumes"),
            {"title": "Portfolio Resume", "file": pdf_file},
            format="multipart",
        )

        response = self.client.get(reverse("auth_api:me"))
        assert response.status_code == status.HTTP_200_OK
        seeker_data = response.data["seeker_profile"]
        assert len(seeker_data["resumes"]) == 1
        assert seeker_data["resumes"][0]["title"] == "Portfolio Resume"
