from biospecdb.qc.qcmanager import QcManager
from biospecdb.qc.qcfilter import QcFilter
from unittest import TestCase


class TestFilter(QcFilter):

    def validate(self, symptoms, sample):
        return True


class QcTests(TestCase):

    def test_manager_add_filter(self):
        m = QcManager()
        f = TestFilter()
        m.register_validator('f', f)
        assert(m.get_validators()['f'] == f)

    def test_run_validations(self):
        m = QcManager()
        m.register_validator('f', TestFilter())
        val = m.validate(None, None)
        assert(val['f'] is True)

    def test_validation_returns_null_on_exception(self):
        m = QcManager()
        f = TestFilter()
        def raise_on_val(x, y):
            raise Exception('error')
        f.validate = raise_on_val
        with self.assertRaises(Exception):
            f.validate(None, None)
        m.register_validator('f', f)
        val = m.validate(None, None)
        assert(val['f'] is None)
