"""Tests for resume_analysis application signals."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.signals import _background_analysis_worker
from talentwright.resume_analysis.signals import on_application_created
from talentwright.resume_analysis.signals import spawn_analysis_thread
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def dummy_app(db):
    employer_user = User.objects.create(email="signals_emp@example.com")
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(employer=employer, title="QA Lead", status=JobStatus.OPEN)
    seeker_user = User.objects.create(email="signals_cand@example.com")
    seeker = SeekerProfile.objects.create(user=seeker_user)
    return Application.objects.create(job=job, seeker=seeker)


@pytest.mark.django_db
def test_signal_skipped_on_update(dummy_app):
    with patch(
        "talentwright.resume_analysis.signals.spawn_analysis_thread"
    ) as mock_spawn:
        on_application_created(
            sender=Application,
            instance=dummy_app,
            created=False,
        )
        mock_spawn.assert_not_called()


@pytest.mark.django_db
def test_signal_skipped_when_pytest_running(monkeypatch, dummy_app):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo")
    with patch(
        "talentwright.resume_analysis.signals.spawn_analysis_thread"
    ) as mock_spawn:
        on_application_created(
            sender=Application,
            instance=dummy_app,
            created=True,
        )
        mock_spawn.assert_not_called()


@pytest.mark.django_db
def test_signal_schedules_background_worker(monkeypatch, dummy_app):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    captured_callbacks = []

    def mock_on_commit(callback):
        captured_callbacks.append(callback)

    with patch("django.db.transaction.on_commit", side_effect=mock_on_commit):
        with patch(
            "talentwright.resume_analysis.signals.spawn_analysis_thread"
        ) as mock_spawn:
            on_application_created(
                sender=Application,
                instance=dummy_app,
                created=True,
            )
            assert len(captured_callbacks) == 1
            # Execute the on_commit callback
            captured_callbacks[0]()
            mock_spawn.assert_called_once_with(dummy_app.id)


@pytest.mark.django_db
def test_background_analysis_worker_execution():
    with patch(
        "talentwright.resume_analysis.signals.analyze_application"
    ) as mock_analyze:
        with patch("django.db.connection.close") as mock_close:
            _background_analysis_worker(999)
            mock_analyze.assert_called_once_with(999)
            mock_close.assert_called_once()


@pytest.mark.django_db
def test_background_analysis_worker_handles_exception():
    with patch(
        "talentwright.resume_analysis.signals.analyze_application",
        side_effect=RuntimeError("DB timeout"),
    ):
        with patch("django.db.connection.close") as mock_close:
            # Should not raise exception
            _background_analysis_worker(999)
            mock_close.assert_called_once()


def test_spawn_analysis_thread_starts_thread():
    with patch("threading.Thread") as mock_thread_class:
        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance

        spawn_analysis_thread(123)

        mock_thread_class.assert_called_once()
        assert mock_thread_class.call_args.kwargs["args"] == (123,)
        assert mock_thread_class.call_args.kwargs["daemon"] is True
        mock_thread_instance.start.assert_called_once()
