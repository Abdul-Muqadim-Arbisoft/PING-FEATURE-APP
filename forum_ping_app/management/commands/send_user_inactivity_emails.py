from datetime import datetime, timedelta
import pytz
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from common.djangoapps.student.models import CourseEnrollment
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
# from your_project.notifications.utils import send_notification  # Adjust this import path to your send_notification()
from forum_ping_app.utils import send_notification


logger = logging.getLogger(__name__)

INACTIVITY_EMAIL_CONFIG = [
    {
        "days": 7,
        "subject": "We haven’t seen you in a few days!",
        "body_intro": "We haven’t seen you on the platform in a few days. A little setback, perhaps?",
        "call_to_action": "Even just a few minutes can help you make progress at your own pace. So why not jump back in today?",
    },
    {
        "days": 14,
        "subject": "Still thinking about you!",
        "body_intro": "We know it’s not always easy to stay focused with everything going on in daily life.",
        "call_to_action": "Even 10 minutes today is a step toward your goals.",
    },
    {
        "days": 30,
        "subject": "It’s been a month — let’s reconnect!",
        "body_intro": "It’s now been a month since you last checked in on your courses. We hope you’re well!",
        "call_to_action": "Even just a few minutes today could bring you closer to your goals.",
    },
    {
        "days": 60,
        "subject": "Two months away... your courses miss you!",
        "body_intro": "It’s been two months since we last saw you on the platform.",
        "call_to_action": "Your courses are still waiting patiently for you 😉",
    },
    {
        "days": 180,
        "subject": "Half a year gone — time to jump back in!",
        "body_intro": "It’s been several months since you last accessed your courses.",
        "call_to_action": "But it’s never too late! Pick up where you left off.",
    },
    {
        "days": 365,
        "subject": "One year later — still your course!",
        "body_intro": "It’s been a year since you enrolled. Maybe it wasn’t the right time?",
        "call_to_action": "Your courses are still here — and your place is still waiting.",
    },
]

NO_ENROLLMENT_EMAIL = {
    "subject": "Welcome to the African Cities Lab platform!",
    "message": (
        "We're thrilled to have you on board!\n\n"
        "You've taken the first step by registering on the platform, and that already shows your "
        "commitment to learning and shaping the future of African cities.\n\n"
        "Now it's time for the next step: enrolling in your first MOOC.\n\n"
        "Our platform offers a growing collection of free, high-quality courses designed to help "
        "you understand and improve urban life across the continent, from mobility and housing "
        "to climate resilience, digital tools, and urban planning.\n\n"
        "👉 Get started now by browsing our available courses below.\n"
    )
}

CATALOG_URL = f"{settings.LMS_ROOT_URL}/courses"

class Command(BaseCommand):
    help = "Sends inactivity reminder emails using ACE-based notification system."

    def handle(self, *args, **options):
        logger.info("Starting inactivity email command...")
        now = datetime.now(pytz.utc)

        for config in INACTIVITY_EMAIL_CONFIG:
            days = config["days"]
            subject = config["subject"]
            intro = config["body_intro"]
            cta = config["call_to_action"]

            cutoff_start = now - timedelta(days=days + 1)
            cutoff_end = now - timedelta(days=days)

            users = self.get_inactive_users(cutoff_start, cutoff_end)
            logger.info(f"Found {users.count()} users inactive for exactly {days} days.")

            for user in users:
                if not user.email:
                    logger.warning(f"Skipping user {user.username}: no email address.")
                    continue

                name = user.first_name or user.username
                enrollments = self.get_active_enrollments(user)

                if not enrollments:
                    # No course enrollments — send platform intro
                    context = {
                        "name": name,
                        "message": NO_ENROLLMENT_EMAIL["message"],
                        "catalog_link": CATALOG_URL,
                        "subject": NO_ENROLLMENT_EMAIL["subject"],
                    }
                    self.send_notification_email(user.email, "thread_mention", context, NO_ENROLLMENT_EMAIL["subject"])
                    logger.info(f"Sent no-enrollment email to {user.email}")
                    continue

                # User has course enrollments — send reminder with all course links
                course_list = []
                for enrollment in enrollments:
                    try:
                        course = CourseOverview.get_from_id(enrollment.course_id)
                        course_link = f"{settings.LMS_ROOT_URL}/courses/{enrollment.course_id}/about"
                        course_list.append({
                            "title": course.display_name,
                            "link": course_link,
                        })
                    except Exception as e:
                        logger.warning(f"Error retrieving course {enrollment.course_id} for user {user.username}: {str(e)}")
                        continue

                if not course_list:
                    logger.warning(f"No valid course links found for user {user.username}. Skipping.")
                    continue

                context = {
                    "name": name,
                    "intro": intro,
                    "call_to_action": cta,
                    "course_list": course_list,
                    "subject": subject,
                }
                self.send_notification_email(user.email, "thread_mention", context, subject)
                logger.info(f"Sent {days}-day inactivity email to {user.email}")

    def get_inactive_users(self, start_date, end_date):
        return User.objects.filter(
            last_login__gt=start_date,
            last_login__lte=end_date,
            is_active=True
        )

    def get_active_enrollments(self, user):
        return CourseEnrollment.objects.filter(
            user=user,
            is_active=True
        )

    def send_notification_email(self, email, message_type, context, subject):
        # from django.contrib.sites.models import Site
        # from django.contrib.auth.models import User
        # try:
        #     request_user = User.objects.get(username="rehman")  # Replace with system user
        # except User.DoesNotExist:
        #     logger.error("Email admin user 'rehman' does not exist.")
        #     return

        # current_site = Site.objects.all().first()
        context.update({
            "subject": subject
        })

        send_notification(
            message_type=message_type,
            data=context,
            subject=subject,
            dest_emails=[email]
        )
