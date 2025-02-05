from openedx.core.djangoapps.ace_common.message import BaseMessageType


class ThreadMentionNotification(BaseMessageType):
    """
    A message for notifying users that they have been mentioned in a post/response/comment on discussion forum.
    """
    APP_LABEL = 'forum_ping_app'
