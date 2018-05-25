import flask
from voluptuous import All, In, Length, Range, Schema

from pulsar import db, APIException
from pulsar.forums.models import (Forum, ForumPost, ForumSubscription, ForumThread,
                                  ForumThreadSubscription)
from pulsar.utils import require_permission, validate_data
from pulsar.validators import bool_get

from . import bp

app = flask.current_app


VIEW_FORUM_THREAD_SCHEMA = Schema({
    'page': All(int, Range(min=0, max=2147483648)),
    'limit': All(int, In((25, 50, 100))),
    'include_dead': bool_get
    })


@bp.route('/forums/threads/<int:id>', methods=['GET'])
@require_permission('view_forums')
@validate_data(VIEW_FORUM_THREAD_SCHEMA)
def view_thread(id: int,
                page: int = 1,
                limit: int = 50,
                include_dead: bool = False) -> flask.Response:
    """
    This endpoint allows users to view details about a forum and its threads.

    .. :quickref: ForumThread; View a forum thread.

    **Example request**:

    .. sourcecode:: http

       GET /forums/threads/1 HTTP/1.1
       Host: pul.sar
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": [
           {
           }
         ]
       }

    :>json list response: A forum thread

    :statuscode 200: View successful
    :statuscode 403: User does not have permission to view thread
    :statuscode 404: Thread does not exist
    """
    thread = ForumThread.from_pk(
        id,
        _404=True,
        include_dead=flask.g.user.has_permission('modify_forum_threads_advanced'))
    thread.set_posts(
        page,
        limit,
        include_dead and flask.g.user.has_permission('modify_forum_posts_advanced'))
    return flask.jsonify(thread)


CREATE_FORUM_THREAD_SCHEMA = Schema({
    'topic': All(str, Length(max=150)),
    'forum_id': All(int, Range(min=0, max=2147483648)),
    }, required=True)


@bp.route('/forums/threads', methods=['POST'])
@require_permission('create_forum_threads')
@validate_data(CREATE_FORUM_THREAD_SCHEMA)
def create_thread(topic: str,
                  forum_id: int) -> flask.Response:
    """
    This is the endpoint for forum thread creation. The ``modify_forum_threads``
    permission is required to access this endpoint.

    .. :quickref: ForumThread; Create a forum thread.

    **Example request**:

    .. sourcecode:: http

       POST /forums/threads HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

       {
         "topic": "How do I get easy ration?",
         "forum_id": 4
       }

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
         }
       }

    :>json dict response: The newly created forum thread

    :statuscode 200: Creation successful
    :statuscode 400: Creation unsuccessful
    """
    thread = ForumThread.new(
        topic=topic,
        forum_id=forum_id,
        poster_id=flask.g.user.id)
    subscribe_users_to_new_thread(thread)
    return flask.jsonify(thread)


def subscribe_users_to_new_thread(thread: ForumThread) -> None:
    """
    Subscribes all users subscribed to the parent forum to the new forum thread.

    :param thread: The newly-created forum thread
    """
    user_ids = ForumSubscription.user_ids_from_forum(thread.forum_id)
    db.session.bulk_save_objects([
        ForumThreadSubscription(user_id=uid, thread_id=thread.id)
        for uid in user_ids])
    ForumThreadSubscription.clear_cache_keys(user_ids=user_ids)


MODIFY_FORUM_THREAD_SCHEMA = Schema({
    'topic': All(str, Length(max=150)),
    'forum_id': All(int, Range(min=0, max=2147483648)),
    'locked': bool_get,
    'sticky': bool_get,
    })


@bp.route('/forums/threads/<int:id>', methods=['PUT'])
@require_permission('modify_forum_threads')
@validate_data(MODIFY_FORUM_THREAD_SCHEMA)
def modify_thread(id: int,
                  topic: str = None,
                  forum_id: int = None,
                  locked: bool = None,
                  sticky: bool = None) -> flask.Response:
    """
    This is the endpoint for forum thread editing. The ``modify_forum_threads``
    permission is required to access this endpoint. The topic, forum_id,
    locked, and sticky attributes can be changed here.

    .. :quickref: ForumThread; Edit a forum thread.

    **Example request**:

    .. sourcecode:: http

       PUT /forums/threads/6 HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

       {
         "topic": "This does not contain typos.",
         "forum_id": 2,
         "locked": true,
         "sticky": false
       }


    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
         }
       }

    :>json dict response: The edited forum thread

    :statuscode 200: Editing successful
    :statuscode 400: Editing unsuccessful
    :statuscode 404: Forum thread does not exist
    """
    thread = ForumThread.from_pk(id, _404=True)
    if topic:
        thread.topic = topic
    if forum_id and Forum.is_valid(forum_id, error=True):
        thread.forum_id = forum_id
    if locked is not None:
        thread.locked = locked
    if sticky is not None:
        thread.sticky = sticky
    db.session.commit()
    return flask.jsonify(thread)


@bp.route('/forums/threads/<int:id>', methods=['DELETE'])
@require_permission('modify_forum_threads_advanced')
def delete_thread(id: int) -> flask.Response:
    """
    This is the endpoint for forum thread deletion . The ``modify_forum_threads_advanced``
    permission is required to access this endpoint. All posts in a deleted forum will also
    be deleted.

    .. :quickref: ForumThread; Delete a forum thread.

    **Example request**:

    .. sourcecode:: http

       DELETE /forums/threads/2 HTTP/1.1
       Host: pul.sar
       Accept: application/json
       Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": {
         }
       }

    :>json dict response: The deleted forum thread

    :statuscode 200: Deletion successful
    :statuscode 400: Deletion unsuccessful
    :statuscode 404: Forum thread does not exist
    """
    thread = ForumThread.from_pk(id, _404=True)
    thread.deleted = True
    ForumPost.update_many(
        pks=ForumPost.get_ids_from_thread(thread.id),
        update={'deleted': True})
    return flask.jsonify(f'ForumThread {id} ({thread.topic}) has been deleted.')


@bp.route('/forums/threads/<int:thread_id>/subscribe', methods=['POST', 'DELETE'])
@require_permission('modify_forum_subscriptions')
def alter_thread_subscription(thread_id: int) -> flask.Response:
    """
    This is the endpoint for forum thread subscription. The ``modify_forum_subscriptions``
    permission is required to access this endpoint. A POST request creates a subscription,
    whereas a DELETE request removes a subscription.

    .. :quickref: ForumThread; Subscribe to a forum thread.

    **Example request**:

    .. sourcecode:: http

       PUT /forums/threads/2/subscribe HTTP/1.1
       Host: pul.sar
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Vary: Accept
       Content-Type: application/json

       {
         "status": "success",
         "response": "Successfully subscribed to thread 2."
       }

    :>json str response: Success or failure message

    :statuscode 200: Subscription alteration successful
    :statuscode 400: Subscription alteration unsuccessful
    :statuscode 404: Forum thread does not exist
    """
    thread = ForumThread.from_pk(thread_id, _404=True)
    subscription = ForumThreadSubscription.from_attrs(
        flask.g.user.id, thread.id)
    if flask.request.method == 'POST':
        if subscription:
            raise APIException(f'You are already subscribed to thread {thread_id}.')
        ForumThreadSubscription.new(
            user_id=flask.g.user.id,
            thread_id=thread_id)
        return flask.jsonify(f'Successfully subscribed to thread {thread_id}.')
    else:  # method = DELETE
        if not subscription:
            raise APIException(f'You are not subscribed to thread {thread_id}.')
        db.session.delete(subscription)
        db.session.commit()
        return flask.jsonify(f'Successfully unsubscribed from thread {thread_id}.')
