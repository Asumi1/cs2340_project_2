from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, JobSeekerProfile
from .models import Application, Job, SavedSearch, Notification


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


class RecruiterPipelineTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter6",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.other_recruiter = CustomUser.objects.create_user(
            username="recruiter7",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker6",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Backend Engineer",
            company_name="MintMatch",
            location="Remote",
            description="Pipeline test",
            is_active=True,
            is_approved=True,
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.jobseeker,
            status="APPLIED",
        )

    def test_owner_recruiter_can_move_candidate_stage(self):
        self.client.login(username="recruiter6", password="testpass123")
        response = self.client.post(
            reverse("update_application_status", args=[self.application.pk]),
            {"status": "SCREENING"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "SCREENING")

    def test_non_owner_recruiter_cannot_move_candidate_stage(self):
        self.client.login(username="recruiter7", password="testpass123")
        response = self.client.post(
            reverse("update_application_status", args=[self.application.pk]),
            {"status": "SCREENING"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "APPLIED")


class JobSearchFilterTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter8",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker8",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.remote_job = Job.objects.create(
            recruiter=self.recruiter,
            title="Remote Backend Engineer",
            company_name="MintMatch",
            location="Atlanta, GA",
            description="Work from anywhere",
            work_mode="REMOTE",
            salary_min=100000,
            salary_max=150000,
            is_active=True,
            is_approved=True,
        )
        self.onsite_job = Job.objects.create(
            recruiter=self.recruiter,
            title="On-site Data Analyst",
            company_name="MintMatch",
            location="Atlanta, GA",
            description="In-office role",
            work_mode="ONSITE",
            salary_min=70000,
            salary_max=90000,
            is_active=True,
            is_approved=True,
        )

    def test_search_filters_by_work_mode(self):
        self.client.login(username="jobseeker8", password="testpass123")
        response = self.client.get(reverse("jobseeker_search"), {"work_mode": "REMOTE"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.remote_job, response.context["jobs"])
        self.assertNotIn(self.onsite_job, response.context["jobs"])

    def test_search_filters_by_salary_range(self):
        self.client.login(username="jobseeker8", password="testpass123")
        response = self.client.get(
            reverse("jobseeker_search"),
            {"min_salary": "120000", "max_salary": "160000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.remote_job, response.context["jobs"])
        self.assertNotIn(self.onsite_job, response.context["jobs"])


class Sprint2MapAndRecommendationTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter9",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.jobseeker = CustomUser.objects.create_user(
            username="jobseeker9",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
        )
        self.profile = JobSeekerProfile.objects.create(
            user=self.jobseeker,
            skills="Python, Django",
            preferred_commute_radius_miles=25,
        )
        self.matching_job = Job.objects.create(
            recruiter=self.recruiter,
            title="Django Developer",
            company_name="MintMatch",
            location="Atlanta, GA",
            description="Build Django apps",
            skills="Django, REST",
            latitude=33.749,
            longitude=-84.388,
            is_active=True,
            is_approved=True,
        )

    def test_jobseeker_dashboard_recommendations_render_without_template_error(self):
        self.client.login(username="jobseeker9", password="testpass123")
        response = self.client.get(reverse("jobseeker_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recommended Jobs")
        self.assertContains(response, "Django Developer")

    def test_jobseeker_can_update_commute_radius_preference(self):
        self.client.login(username="jobseeker9", password="testpass123")
        response = self.client.post(
            reverse("update_commute_radius_preference"),
            {"radius_miles": "10"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.preferred_commute_radius_miles, 10)


class SavedSearchNotificationTests(TestCase):
    def setUp(self):
        self.recruiter = CustomUser.objects.create_user(
            username="recruiter10",
            password="testpass123",
            role=CustomUser.Role.RECRUITER,
        )
        self.candidate = CustomUser.objects.create_user(
            username="candidate10",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
            first_name="Ari",
            last_name="Stone",
        )
        JobSeekerProfile.objects.create(
            user=self.candidate,
            skills="Python, SQL",
            is_resume_public=True,
        )

    def test_saved_search_stores_initial_match_count(self):
        self.client.login(username="recruiter10", password="testpass123")
        response = self.client.post(
            reverse("save_search"),
            {
                "name": "Python candidates",
                "query": "Python",
                "location": "",
                "skill": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        saved = SavedSearch.objects.get(recruiter=self.recruiter)
        self.assertEqual(saved.last_match_count, 1)

    def test_new_matches_trigger_notification_once(self):
        saved = SavedSearch.objects.create(
            recruiter=self.recruiter,
            name="Python candidates",
            query="Python",
            last_match_count=1,
        )
        new_candidate = CustomUser.objects.create_user(
            username="candidate11",
            password="testpass123",
            role=CustomUser.Role.JOBSEEKER,
            first_name="Sam",
            last_name="Reed",
        )
        JobSeekerProfile.objects.create(
            user=new_candidate,
            skills="Python",
            is_resume_public=True,
        )

        self.client.login(username="recruiter10", password="testpass123")
        first_hit = self.client.get(reverse("recruiter_talent_search"))
        self.assertEqual(first_hit.status_code, 200)

        saved.refresh_from_db()
        self.assertEqual(saved.last_match_count, 2)
        self.assertEqual(Notification.objects.filter(user=self.recruiter).count(), 1)

        second_hit = self.client.get(reverse("recruiter_talent_search"))
        self.assertEqual(second_hit.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.recruiter).count(), 1)
