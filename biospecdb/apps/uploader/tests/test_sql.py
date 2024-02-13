import pytest

from django.core.exceptions import SuspiciousOperation
from django.db.utils import OperationalError

from uploader.models import Observable
from uploader.sql import drop_view, execute_sql, secure_name, update_view


@pytest.mark.django_db(databases=["default", "bsr"])
class TestSQL:
    db = "bsr"

    def test_ok_secure_name(self):
        secure_name("my_table1")

    def test_not_ok_secure_name(self):
        with pytest.raises(SuspiciousOperation):
            secure_name("; drop view my_table")

    def test_execute_sql(self, observables):
        results = execute_sql("select * from observable order by name", db=self.db)
        observables = Observable.objects.all().order_by("name")
        for d1, d2 in zip(results, observables):
            assert d1["name"] == d2.name

    def test_drop_nonexistent_view(self, db):
        drop_view("khbihb", db=self.db)

    def test_update_view(self, db, observables):
        view = "my_view"
        resp1 = update_view(view,
                            f"""
                            create view {view} as
                            select *
                            from observable
                            """,
                            check=True,
                            limit=None,
                            db=self.db
                            )

        resp2 = execute_sql(f"select * from {view}", db=self.db)
        assert resp1 == resp2

    def test_non_persistent_test_view(self, db):
        with pytest.raises(OperationalError, match="no such table:"):
            execute_sql("select * from my_view", db=self.db)

    def test_update_view_limit(self, db, observables):
        view = "my_view"
        limit = 1

        resp1 = update_view(view,
                            f"""
                            create view {view} as
                            select *
                            from observable
                            """,
                            check=True,
                            limit=limit,
                            db=self.db
                            )
        assert len(resp1) == limit

    def test_update_view_check(self, db, observables):
        view = "my_view"

        with pytest.raises(OperationalError, match="syntax error"):
            update_view(view,
                        f"""
                        ceate view {view} as -- note typo in create
                        select *
                        from observable
                        """,
                        check=True,
                        db=self.db
                        )

    def test_update_view_check_transactional(self, db, observables):
        view = "my_view"

        update_view(view,
                    f"""
                    create view {view} as
                    select *
                    from observable
                    """,
                    check=True,
                    db=self.db
                    )

        with pytest.raises(OperationalError, match="syntax error"):
            update_view(view,
                        f"""
                        ceate view {view} as -- note typo in create
                        select *
                        from observable
                        """,
                        check=True,
                        db=self.db
                        )

        # With SQLite views need to be dropped then re-added (there's no alter). ``update_view()`` isn't completely
        # transactional such that a failed update won't roll back the previous view state. Therefore, the above failed
        # update will result in the view not being present if it were before.
        sql = f"select * from {view}"  # nosec B608
        with pytest.raises(OperationalError, match="no such table:"):
            execute_sql(sql)

    def test_drop_view(self, db, observables):
        view = "my_view"
        update_view(view,
                    f"""
                        create view {view} as
                        select *
                        from observable
                        """,
                    db=self.db
                    )
        resp = execute_sql(f"select * from {view}", db=self.db)
        assert len(resp) == Observable.objects.count()
        drop_view(view, db=self.db)
        with pytest.raises(OperationalError, match="no such table:"):
            execute_sql(f"select * from {view}", db=self.db)

    def test_correct_db(self, mock_data_from_files):
        resp = execute_sql("select * from patient", db=self.db)
        assert len(resp) == 10

    def test_incorrect_db(self, mock_data_from_files):
        with pytest.raises(OperationalError, match="no such table:"):
            execute_sql("select * from patient", db="default")
