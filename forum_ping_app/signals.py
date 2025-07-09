from django.dispatch import receiver
from django.contrib.sites.models import Site

from openedx.core.djangoapps.django_comment_common.signals import (
    comment_created, comment_edited, thread_created, thread_edited,
)
from openedx.core.djangoapps.theming.helpers import get_current_site

from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from django.db.models.signals import post_save
from .utils import (
    is_discussion_notification_configured_for_site, update_context_with_comment,
    update_context_with_thread, build_discussion_notification_context
)
from .tasks import send_thread_mention_email_task
from logging import getLogger
log = getLogger(__name__)


@receiver(comment_created)
@receiver(comment_edited)
@receiver(thread_edited)
@receiver(thread_created)
def send_thread_mention_email_notification(sender, user, post, **kwargs):
    """
    This function will retrieve list of tagged usernames from discussion post/response
    and then send email notifications to all tagged usernames.
    Arguments:
        sender: Model from which we received signal (we are not using it in this case).
        user: Thread/Comment owner
        post: Thread/Comment that is being created/edited
        current_site: The current site of the discussion
        kwargs: Remaining key arguments of signal.
    """
    import pdb
    pdb.set_trace()
    log.info("Working woriking good good hahah")
    current_site = get_current_site()


    if current_site is None:
        current_site = Site.objects.get_current()

    is_thread = post.type == 'thread'
    # if not is_discussion_notification_configured_for_site(current_site, post.id):
    #     return
    course_key = CourseKey.from_string(post.course_id)
    # course_overview = CourseOverview.get_from_id(post.course_id)
    # course_name = course_overview.display_name
    context = {
        'course_id': course_key,
        # 'course_name':course_name,
        'site': current_site,
        'is_thread': is_thread
    }
    if is_thread:
        update_context_with_thread(context, post)
    else:
        update_context_with_thread(context, post.thread)
        update_context_with_comment(context, post)
    message_context = build_discussion_notification_context(context)
    send_thread_mention_email_task.delay(post.body, message_context, is_thread)

@receiver(post_save, sender=CourseOverview)
def upload_course_default_image(sender, instance, created, **kwargs):
    log.info("Working woriking good good hahah")
    var="testing"
    