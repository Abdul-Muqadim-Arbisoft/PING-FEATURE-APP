import logging
import markdown
import pytz
from datetime import datetime
import json

from edx_ace import ace
from edx_ace.recipient import Recipient

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.utils.timezone import localtime
from django.urls import reverse

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.ace_common.template_context import get_base_template_context
from lms.djangoapps.discussion.tasks import _get_thread_url
from openedx.core.lib.celery.task_utils import emulate_http_request

from .message_types import ThreadMentionNotification

log = logging.getLogger(__name__)
ENABLE_FORUM_NOTIFICATIONS_FOR_SITE_KEY = 'enable_forum_notifications'
User = get_user_model()

MESSAGE_TYPES = {
    'thread_mention': ThreadMentionNotification,
}


def is_discussion_notification_configured_for_site(site, post_id):
    if site is None:
        log.info('Discussion: No current site, not sending notification about new thread: %s.', post_id)
        return False
    try:
        if not site.configuration.get_value(ENABLE_FORUM_NOTIFICATIONS_FOR_SITE_KEY, False):
            log_message = 'Discussion: notifications not enabled for site: %s. Not sending message about new thread: %s'
            log.info(log_message, site, post_id)
            return False
    except SiteConfiguration.DoesNotExist:
        log_message = 'Discussion: No SiteConfiguration for site %s. Not sending message about new thread: %s.'
        log.info(log_message, site, post_id)
        return False
    return True


def update_context_with_thread(context, thread):
    thread_author = User.objects.get(id=thread.user_id)
    log.info("thread_author.username is :%s", thread_author.username)
    created_at_datetime = datetime.strptime(thread.created_at, "%Y-%m-%dT%H:%M:%SZ")
    created_at_datetime = created_at_datetime.replace(tzinfo=pytz.utc)
    formatted_date = localtime(created_at_datetime).date()
    formatted_date = formatted_date.strftime('%Y-%m-%d')
    context.update({
        'thread_id': thread.id,
        'thread_title': thread.title,
        'thread_body': markdown.markdown(thread.body),
        'thread_commentable_id': thread.commentable_id,
        'thread_author_id': thread_author.id,
        'thread_username': thread_author.username,
        'thread_created_at': formatted_date
    })


def update_context_with_comment(context, comment):
    comment_author = User.objects.get(id=comment.user_id)
    context.update({
        'comment_id': comment.id,
        'comment_body': markdown.markdown(comment.body),
        'comment_author_id': comment_author.id,
        'comment_username': comment_author.username,
        'comment_created_at': comment.created_at
    })


def build_discussion_notification_context(context):
    site = context['site']
    message_context = get_base_template_context(site)
    message_context.update(context)
    message_context.update({
        'site_id': site.id,
        'post_link': _get_thread_url(context),
        'course_name': CourseOverview.get_from_id(message_context.pop('course_id')).display_name
    })
    message_context.pop('site')
    return message_context


def get_mentioned_users_list(input_string, users_list=None):
    if not users_list:
        users_list = []

    start_index = input_string.find("@")
    if start_index == -1:
        return users_list
    else:
        end_index = input_string[start_index:].find(" ")
        name = input_string[start_index:][:end_index]

        try:
            user = User.objects.get(username=name[1:])  # remove @ from name
            users_list.append(user)
        except User.DoesNotExist:
            log.error("Unable to find mentioned thread user with name: {}".format(name))

        # remove tagged name from string and search for next tagged name
        remianing_string = input_string.replace(name, "")
        return get_mentioned_users_list(remianing_string, users_list)


# def send_ace_message(request_user, request_site, dest_email, context, message_class):
#     with emulate_http_request(site=request_site, user=request_user):
#         message = message_class().personalize(
#             recipient=Recipient(lms_user_id=0, email_address=dest_email),
#             language='en',
#             user_context=context,
#         )
#         log.info('Sending email notification with context %s', context)
#         ace.send(message)
def send_ace_message(request_user, request_site, dest_email, context, message_class):
    log.info("Attempting to send via ACE...")
    # pdb.set_trace()
    try:
        with emulate_http_request(site=request_site, user=request_user):
            log.info(f"Creating ACE message for {dest_email}")
            
            # Debug: Print the context being used
            log.info(f"Message context: {context}")
            
            message = message_class().personalize(
                recipient=Recipient(lms_user_id=0, email_address=dest_email),
                language='en',
                user_context=context,
            )
            
            log.info(f"Message object created: {message}")
            
            # Debug: Check if ACE is configured to send
            log.info("Attempting to send via ACE...")
            ace.send(message)
            log.debug("message sent testing")
            
            log.info(f"Email sent to {dest_email} via ACE")
            return True
    except Exception as e:
        log.error(f"Failed to send ACE email to {dest_email}: {str(e)}")
        return False

def send_notification(message_type, data, subject, dest_emails, request_user=None, current_site=None):
    """
    Send an email
    Arguments:
        message_type - string value to select ace message object
        data - Dict containing context/data for the template
        subject - Email subject
        dest_emails - List of destination emails
    Returns:
        a boolean variable indicating email response.
        if email is successfully send to all dest emails -> return True otherwise return false.
    """
   
    log.info("i am here")
    
    if not current_site:
        current_site = Site.objects.all().first()

    if not request_user:
        try:
            request_user = User.objects.get(username="11")
        except User.DoesNotExist:
            log.error(
                "Unable to send email as Email Admin User with username: {} does not exist.".format(
                    'rehman')
            )
            return

    data.update({'subject': subject})

    message_context = get_base_template_context(current_site)
    message_context.update(data)
    content = json.dumps(message_context)

    message_class = MESSAGE_TYPES[message_type]
    return_value = True

    base_root_url = current_site.configuration.get_value('LMS_ROOT_URL')


    message_context.update({
        "site_name":  current_site.configuration.get_value('platform_name'),
        "logo_url": 'https://courses.africancitieslab.org/static/indigo/images/logo.7fd3f2a54402.png',
    })
    for email in dest_emails:
        message_context.update({
            "email": email
        })
        try:
            send_ace_message(request_user, current_site, email, message_context, message_class)
            log.info(
                'Email has been sent to "%s" for content %s.',
                email,
                content
            )
        except Exception as e:
            log.error(
                'Unable to send an email to %s for content "%s"',
                email,
                content
            )
            log.error(e)
            return_value = False

    return return_value


def send_thread_mention_email(receivers, context, is_thread=True):
    log.info("Sending thread mention email to users: {}".format(receivers))
    key = "thread_mention"

    if is_thread:
        mentioned_by = context.get("thread_username")
    else:
        mentioned_by = context.get("comment_username")

    context.update({
        "mentioned_by": mentioned_by,
    })

    send_notification(key, context, "", receivers)
