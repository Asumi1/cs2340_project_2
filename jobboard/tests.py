from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from .models import Application, Job


class JobApplyFlowTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter1",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker1",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Backend Engineer",
            company_name="MintMatch",
            location="Atlanta, GA",
            description="Build APIs",
            is_active=True,
            is_approved=True,
        )

    def test_jobseeker_apply_creates_application(self):
        self.client.login(username="jobseeker1", password="testpass123")
        response = self.client.post(reverse("job_apply", args=[self.job.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Application.objects.filter(job=self.job, applicant=self.jobseeker).exists()
        )

    def test_duplicate_application_is_blocked(self):
        Application.objects.create(job=self.job, applicant=self.jobseeker, status="APPLIED")
        self.client.login(username="jobseeker1", password="testpass123")
        response = self.client.post(reverse("job_apply", args=[self.job.pk]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Application.objects.filter(job=self.job, applicant=self.jobseeker).count(), 1
        )


class RecruiterKanbanSelectionTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter2",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker2",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.new_job_no_apps = Job.objects.create(
            recruiter=self.recruiter,
            title="Newest Job",
            company_name="MintMatch",
            location="Remote",
            description="No applicants yet",
            is_active=True,
            is_approved=True,
        )
        self.older_job_with_apps = Job.objects.create(
            recruiter=self.recruiter,
            title="Older Job",
            company_name="MintMatch",
            location="Atlanta, GA",
            description="Has applicants",
            is_active=True,
            is_approved=True,
        )
        Application.objects.create(
            job=self.older_job_with_apps,
            applicant=self.jobseeker,
            status="APPLIED",
        )

    def test_kanban_defaults_to_job_with_applications(self):
        self.client.login(username="recruiter2", password="testpass123")
        response = self.client.get(reverse("recruiter_kanban"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_job"].pk, self.older_job_with_apps.pk)
        self.assertEqual(response.context["total_applications_count"], 1)


class OneClickApplyTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter3",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker3",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="UI Engineer",
            company_name="MintMatch",
            location="Remote",
            description="Build web UI",
            is_active=True,
            is_approved=True,
        )
        self.next_job = Job.objects.create(
            recruiter=self.recruiter,
            title="Frontend Engineer",
            company_name="MintMatch",
            location="Remote",
            description="Build frontend",
            is_active=True,
            is_approved=True,
        )

    def test_one_click_submit_creates_application_and_redirects(self):
        self.client.login(username="jobseeker3", password="testpass123")
        response = self.client.post(
            reverse("one_click_apply_submit", args=[self.job.pk]),
            {"tailored_note": "Excited to apply."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Application.objects.filter(
                job=self.job,
                applicant=self.jobseeker,
                cover_letter="Excited to apply.",
            ).exists()
        )

    def test_one_click_duplicate_is_blocked(self):
        Application.objects.create(job=self.job, applicant=self.jobseeker, status="APPLIED")
        self.client.login(username="jobseeker3", password="testpass123")
        response = self.client.post(
            reverse("one_click_apply_submit", args=[self.job.pk]),
            {"tailored_note": "Duplicate attempt"},
        )

        self.assertEqual(response.status_code, 400)

    def test_one_click_form_redirects_to_next_unapplied_job(self):
        Application.objects.create(job=self.job, applicant=self.jobseeker, status="APPLIED")
        self.client.login(username="jobseeker3", password="testpass123")
        response = self.client.get(reverse("one_click_apply_form", args=[self.job.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("one_click_apply_form", args=[self.next_job.pk]),
            response.url,
        )


class ApplicationTrackingStageTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter4",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker4",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.jobseeker_alt = CustomUser.objects.create_user(
            username="jobseeker5",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Software Engineer",
            company_name="MintMatch",
            location="Remote",
            description="Build features",
            is_active=True,
            is_approved=True,
        )

    def test_screening_maps_to_review_for_tracking(self):
        app = Application.objects.create(
            job=self.job,
            applicant=self.jobseeker,
            status="SCREENING",
        )
        self.assertEqual(app.get_tracking_stage_display(), "Review")
        self.assertEqual(app.get_tracking_stage_step(), 2)

    def test_hired_and_rejected_map_to_closed_for_tracking(self):
        hired_app = Application.objects.create(
            job=self.job,
            applicant=self.jobseeker,
            status="HIRED",
        )
        rejected_app = Application.objects.create(
            job=self.job,
            applicant=self.jobseeker_alt,
            status="REJECTED",
        )
        self.assertEqual(hired_app.get_tracking_stage_display(), "Closed")
        self.assertEqual(hired_app.get_tracking_stage_step(), 5)
        self.assertEqual(rejected_app.get_tracking_stage_display(), "Closed")
        self.assertEqual(rejected_app.get_tracking_stage_step(), 5)


class AdminModerationTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="admin1",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
            is_staff=True,
            is_superuser=True,
        )
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter5",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Spam Job",
            company_name="BadCo",
            location="Remote",
            description="Unwanted posting",
            is_active=True,
            is_approved=True,
        )

    def test_admin_dashboard_contains_live_job_for_moderation(self):
        self.client.login(username="admin1", password="testpass123")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.job, response.context["moderation_jobs"])

    def test_admin_can_remove_live_job(self):
        self.client.login(username="admin1", password="testpass123")
        response = self.client.post(
            reverse("approve_job", args=[self.job.pk]),
            {"remove": "1"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_active)
