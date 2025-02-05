from logging import getLogger
import markdown

from celery import shared_task
from celery_utils.logged_task import LoggedTask

from .utils import (get_mentioned_users_list, send_thread_mention_email)

log = getLogger(__name__)


@shared_task(base=LoggedTask)
def send_thread_mention_email_task(post_body, context, is_thread):
    log.info("Initiated task to send thread mention notifications.")

    # convert markdown post_body to html
    processed_post_body = markdown.markdown(post_body)

    # Replace few chars to handle cases i.e "<h1>@username</h1>" or <h1>@username/n</h1> so it will be easy
    # to retrieve mentioned usernames as usernames will be in between '@' and ' ' characters in processed_post_body.
    processed_post_body = processed_post_body.replace("\n", " ").replace("</", " ")

    users_list = get_mentioned_users_list(processed_post_body)

    if users_list:
        receipients = [user.email for user in users_list]
        send_thread_mention_email(receipients, context, is_thread)
    else:
        log.info("No user is tagged on thread/comment of discussion forum.")
