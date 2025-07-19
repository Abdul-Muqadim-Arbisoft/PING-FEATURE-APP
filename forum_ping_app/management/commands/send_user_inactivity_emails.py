from datetime import datetime, timedelta
import pytz
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from common.djangoapps.student.models import CourseEnrollment
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.models import UserPreference
# from your_project.notifications.utils import send_notification  # Adjust this import path to your send_notification()
from forum_ping_app.utils import send_notification


logger = logging.getLogger(__name__)

INACTIVITY_EMAIL_CONFIG_EN = [
    {
        "days": 7,
        "subject": "We haven’t seen you in a few days!",
        "greeting": "Hello {name},",
        "body_intro": (
            "We haven’t seen you on the African Cities Lab learning platform in a few days. "
            "A little setback, perhaps?\n\n"
            "No worries! Your courses are still here, ready for you to pick up right where you left off!"
        ),
        "call_to_action": "Even just a few minutes can help you make progress at your own pace.\nSo why not jump back in today?",
        "closing": "See you soon on the platform!\nThe course team",
    },
    {
        "days": 14,
        "subject": "Still thinking about you!",
        "greeting": "Hello {name},",
        "body_intro": (
            "We know it’s not always easy to stay focused with everything going on in daily life.\n\n"
            "But here’s some good news: the African Cities Lab learning platform is still here, just as you left it!"
        ),
        "call_to_action": "Jumping back in, even for just 10 minutes, is already one step closer to your learning goals.\nSo go for it!",
        "closing": "See you soon!\nThe course team",
    },
    {
        "days": 30,
        "subject": "It’s been a month — let’s reconnect!",
        "greeting": "Hello {name},",
        "body_intro": (
            "It’s now been a month since your last visit to the African Cities Lab learning platform. "
            "We hope everything is going well for you!\n\nMaybe you’ve been really busy? "
            "Or maybe you simply forgot that your learning journey is still just a click away?"
        ),
        "call_to_action": "Spending just a few minutes today could bring you one step closer to your goals. It’s never too late!",
        "closing": "See you soon!\nThe course team",
    },
    {
        "days": 60,
        "subject": "Two months away... your courses miss you!",
        "greeting": "Hello {name},",
        "body_intro": (
            "It’s now been two months since we last saw you on the African Cities Lab learning platform ... but it’s never too late!\n\n"
            "Our courses are still available and waiting patiently for you to return to your learning journey 😉"
        ),
        "call_to_action": "Your motivation is just one click away!",
        "closing": "See you soon!\nThe course team",
    },
    {
        "days": 180,
        "subject": "Half a year gone — time to jump back in!",
        "greeting": "Hello {name},",
        "body_intro": (
            "It’s been several months since you last accessed the African Cities Lab learning platform ☹\n\n"
            "But don’t worry! Courses are still here, ready for you to pick up at your own pace!"
        ),
        "call_to_action": "Why not get back to it today? Even just a few minutes can make a real difference!",
        "closing": "See you soon!\nThe course team",
    },
    {
        "days": 365,
        "subject": "One year later — still your course!",
        "greeting": "Hello {name},",
        "body_intro": (
            "It’s been a year since you enrolled in the African Cities Lab learning platform. Maybe it just wasn’t the right time for you?\n\n"
            "Courses are still here. And your place is still waiting for you!"
        ),
        "call_to_action": "Ready to start again from the beginning? Or curious to explore what’s new?",
        "closing": "We’d love to see you back!\nThe course team",
    },
]

NO_ENROLLMENT_EMAIL_EN = {
    "subject": "Welcome to the African Cities Lab platform!",
    "greeting": "Hello {name},",
    "message": (
        "We're thrilled to have you on board!\n\n"
        "You've taken the first step by registering on the African Cities Lab learning platform, and that already shows your "
        "commitment to learning and shaping the future of African cities.\n\n"
        "Now it's time for the next step: enrolling in your first MOOC.\n\n"
        "Our platform offers a growing collection of free, high-quality courses designed to help "
        "you understand and improve urban life across the continent, from mobility and housing "
        "to climate resilience, digital tools, and urban planning.\n\n"
        "Get started now by browsing our available courses:\n[Link to course catalog]\n\n"
        "Whether you're a student, professional, city official, or just passionate about urban change, there's a MOOC waiting for you.\n\n"
        "We’re excited to support your learning and be part of your journey toward more inclusive, sustainable, and innovative African cities."
    ),
    "closing": "Warm regards,\nThe African Cities Lab Team",
}
NO_ENROLLMENT_EMAIL_FR = {
    "subject": "Bienvenue sur la plateforme de l’African Cities Lab !",
    "greeting": "Bonjour {name},",
    "message": (
        "Nous sommes ravis de vous accueillir sur la plateforme de formation de l’African Cities Lab !\n\n"
        "Vous avez déjà franchi une première étape importante en vous inscrivant, et cela témoigne de votre engagement envers "
        "la transformation des villes africaines.\n\n"
        "Il est maintenant temps de passer à l’étape suivante : vous inscrire à votre premier MOOC !\n\n"
        "Notre plateforme propose une offre croissante de cours gratuits et de haute qualité, conçus pour vous aider "
        "à mieux comprendre et améliorer la vie urbaine à travers le continent, qu’il s’agisse de mobilité, de logement, "
        "de résilience climatique, d’outils numériques ou encore de planification urbaine.\n\n"
        "Commencez dès maintenant en explorant les cours disponibles :\n[Lien vers le catalogue des cours]\n\n"
        "Que vous soyez étudiant·e, professionnel·le, agent municipal ou simplement passionné·e par les enjeux urbains, "
        "un MOOC vous attend.\n\n"
        "Nous sommes heureux de vous accompagner dans votre parcours d’apprentissage et de faire partie de votre engagement "
        "pour des villes africaines plus inclusives, durables et innovantes."
    ),
    "closing": "À très vite !\nL’équipe de l’African Cities Lab",
}
INACTIVITY_EMAIL_CONFIG_FR = [
    {
        "days": 7,
        "subject": "Cela fait quelques jours que nous ne vous avons pas vu !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Nous n’avons pas eu le plaisir de vous voir sur la plateforme de formation de l’African Cities Lab depuis quelques jours. "
            "Un petit contretemps, peut-être ?\n\n"
            "Pas d’inquiétude ! Les cours sont là et n’attendent plus que vous !"
        ),
        "call_to_action": (
            "Même quelques minutes suffisent pour progresser à votre rythme.\n"
            "Alors pourquoi ne pas reprendre aujourd’hui ?"
        ),
        "closing": "À très vite !\nL’équipe pédagogique",
    },
    {
        "days": 14,
        "subject": "On pense toujours à vous !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Nous avons conscience qu’il n’est pas toujours facile de rester concentré dans le rythme du quotidien.\n\n"
            "Mais bonne nouvelle : la plateforme de formation de l’African Cities Lab vous attend, intacte !"
        ),
        "call_to_action": (
            "Reprendre maintenant, même pour 10 minutes, c’est déjà un pas de plus vers vos objectifs.\n"
            "Alors lancez-vous !"
        ),
        "closing": "À très vite,\nL’équipe pédagogique",
    },
    {
        "days": 30,
        "subject": "Un mois s’est écoulé — reconnectons-nous !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Cela fait maintenant un mois que vous n’avez pas consulté la plateforme de formation de l’African Cities Lab. "
            "Nous espérons que tout va bien pour vous !\n\n"
            "Peut-être avez-vous été très pris(e) ? Ou avez-vous tout simplement oublié que votre projet de formation "
            "était toujours à portée de clic ?"
        ),
        "call_to_action": (
            "Reprendre quelques minutes aujourd’hui pourrait vous rapprocher de vos objectifs !\n"
            "Il n’est jamais trop tard !"
        ),
        "closing": "À très vite !\nL’équipe pédagogique",
    },
    {
        "days": 60,
        "subject": "Deux mois d’absence… vos cours vous attendent !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Cela fait maintenant deux mois que nous ne vous avons pas vu sur la plateforme de formation de l’African Cities Lab "
            "mais il n’est jamais trop tard !\n\n"
            "Les cours sont toujours disponibles, et ils attendent patiemment que vous repreniez vos apprentissages 😉"
        ),
        "call_to_action": "Votre motivation est là, à portée de clic !",
        "closing": "À très vite !\nL’équipe pédagogique",
    },
    {
        "days": 180,
        "subject": "Six mois plus tard — il est temps de revenir !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Cela fait maintenant plusieurs mois que vous n’avez pas consulté la plateforme de formation de l’African Cities Lab ☹\n\n"
            "Sachez que les cours sont toujours là, disponibles, prêts à être consultés à votre rythme..."
        ),
        "call_to_action": (
            "Pourquoi ne pas reprendre aujourd’hui ?\n"
            "Même quelques minutes peuvent faire toute la différence !"
        ),
        "closing": "À très vite !\nL’équipe pédagogique",
    },
    {
        "days": 365,
        "subject": "Un an plus tard — votre cours est toujours là !",
        "greeting": "Bonjour {name},",
        "body_intro": (
            "Un an s’est écoulé depuis votre inscription sur la plateforme de formation de l’African Cities Lab. "
            "Peut-être n’était-ce pas le bon moment pour vous ?\n\n"
            "Les cours sont toujours là. Et vous avez toujours votre place !"
        ),
        "call_to_action": (
            "Envie de recommencer depuis le début ou de découvrir nos nouveautés ?"
        ),
        "closing": "Au plaisir de vous revoir très vite !\nL’équipe pédagogique",
    },
]


CATALOG_URL = f"{settings.LMS_ROOT_URL}/courses"

class Command(BaseCommand):
    help = "Sends inactivity reminder emails using ACE-based notification system."

    def handle(self, *args, **options):
        logger.info("Starting inactivity email command...")
        now = datetime.now(pytz.utc)

        for config_en, config_fr in zip(INACTIVITY_EMAIL_CONFIG_EN, INACTIVITY_EMAIL_CONFIG_FR):
            days = config_en["days"]  

            cutoff_start = now - timedelta(days=days + 1)
            cutoff_end = now - timedelta(days=days)

            users = self.get_inactive_users(cutoff_start, cutoff_end)
            logger.info(f"Found {users.count()} users inactive for exactly {days} days.")

            for user in users:
                if not user.email:
                    logger.warning(f"Skipping user {user.username}: no email address.")
                    continue

                # Get user language preference
                language_preference = UserPreference.get_value(user, "pref-lang", default="en").lower()
                if language_preference in ["fr", "fr-ca"]:
                    config = config_fr
                    no_enrollment_email = NO_ENROLLMENT_EMAIL_FR
                else:
                    config = config_en
                    no_enrollment_email = NO_ENROLLMENT_EMAIL_EN

                name = user.first_name or user.username
                enrollments = self.get_active_enrollments(user)

                if not enrollments:
                    # No course enrollments — send platform intro
                    context = {
                        "name": name,
                        "message": no_enrollment_email["message"],
                        "language": language_preference[:2],
                        "catalog_link": CATALOG_URL,
                        "subject": no_enrollment_email["subject"],
                        "greeting": no_enrollment_email["greeting"].format(name=name),
                        "closing": no_enrollment_email["closing"],
                        "course_list": []

                    }
                    self.send_notification_email(user.email, "thread_mention", context, no_enrollment_email["subject"])
                    logger.info(f"Sent no-enrollment email to {user.email}")
                    continue

                # User has course enrollments — send reminder
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

                greeting = config["greeting"].format(name=name)
                context = {
                    "name": name,
                    "intro": config["body_intro"],
                    "call_to_action": config["call_to_action"],
                    "course_list": course_list,
                    "subject": config["subject"],
                    "language": language_preference[:2],
                    "greeting": greeting,
                    "closing": config["closing"]
                }
                self.send_notification_email(user.email, "thread_mention", context, config["subject"])
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
