import re

from django.core.exceptions import SuspiciousOperation
from django.db import connection, transaction
from django.db.utils import OperationalError


def secure_name(name):
    if re.search(r"[^_a-zA-Z0-9]", name):
        raise SuspiciousOperation(f"SQL security issue! Expected name consisting of only [_a-zA-Z] but got '{name}'")


def execute_sql(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        if not result:
            return
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]


def drop_view(view):
    secure_name(view)
    try:
        execute_sql(f"drop view {view}")  # nosec B608
    except OperationalError as error:
        if "no such view:" not in str(error):
            raise


def update_view(view, sql, params=None, check=True, limit=1):
    """ SQLite can't alter views, so they must first be dropped and then re-added. """
    secure_name(view)

    # NOTE: We don't include the drop within the transaction. If the view requires updating but fails, it seems safer to
    # have no view rather than potentially blindly (to a user) rolling back to the outdated view.
    # If this behaviour isn't desired, ensure that whatever triggers the need for an update (the caller) is also
    # transactional around the DB update and this call, e.g., see ``uploader.base_models.ModelWithViewDependency.save``.
    # That way the old view _will_ be rolled back if the below check fails but so will the cause of update such that the
    # view is still correct for the rolled back DB state.
    # This behaviour also facilitates trivial testing.
    drop_view(view)

    with transaction.atomic():
        execute_sql(sql, params=params)

        # The view isn't actually used upon creation so may contain latent errors. To check for errors, we query it so
        # that it complains upon creation not later upon usage.
        if check:
            sql = f"select * from {view}"  # nosec B608
            params = []
            if limit:
                sql += " limit %s"
                params.append(limit)
            return execute_sql(sql, params=params)