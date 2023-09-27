
class BaseRouter:
    route_app_labels = {}
    exclude_app_labels = {}
    db = None

    def _allowed(self, obj):
        if (obj not in self.exclude_app_labels) and (obj in self.route_app_labels):
            return self.db
        return False

    def db_for_read(self, model, **hints):
        return self._allowed(model._meta.app_label)

    db_for_write = db_for_read

    def allow_relation(self, obj1, obj2, **hints):
        if self._allowed(obj1._meta.app_label) or self._allowed(obj2._meta.app_label):
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if self._allowed(app_label):
            return db == self.db
        return False


class BSRRouter(BaseRouter):
    route_app_labels = {"uploader"}
    db = "bsr"


class AdminRouter(BaseRouter):
    route_app_labels = {}
    exclude_app_labes = {"uploader"}
    db = "admin"
