import pytest

from uploader.tests.conftest import SimpleQueryFactory
from uploader.charts import count_bool_observables, get_pie_chart, get_line_chart


@pytest.fixture()
def query(request):
    sql_marker = request.node.get_closest_marker("sql")
    sql = sql_marker.args[0] if sql_marker and sql_marker.args[0] else "select * from spectral_data"

    q = SimpleQueryFactory(sql=sql)
    results = q.execute_query_only()
    return results


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCharts:
    def test_empty_count_bool_observables(self, query):
        df = count_bool_observables(query)
        assert df is None

    @pytest.mark.sql("select * from full_patient")
    def test_get_pie_chart(self, mock_data_from_files, sql_views, query):
        html = get_pie_chart(query)
        assert html

    @pytest.mark.sql("select * from full_patient")
    def test_get_line_chart(self, mock_data_from_files, sql_views, query):
        html = get_line_chart(query)
        assert html

    def test_empty_get_pie_chart(self, query):
        assert get_pie_chart(query) is None

    def test_empty_get_line_chart(self, query):
        assert get_line_chart(query) is None
