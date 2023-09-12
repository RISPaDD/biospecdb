from pathlib import Path

from django.conf import settings
import django.core.files
from django.core.management import call_command
import pytest

from uploader.models import UploadedFile
from uploader.forms import DataInputForm

DATA_PATH = Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def sql_views(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('update_sql_views')


@pytest.fixture(scope="function")
def diseases(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'diseases.json')


@pytest.fixture(scope="function")
def instruments(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'instruments.json')


@pytest.fixture(scope="function")
def patients(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'biospecdb/apps/uploader/tests/data/patients.json')


@pytest.fixture(scope="function")
def visits(patients, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'biospecdb/apps/uploader/tests/data/visits.json')


@pytest.fixture(scope="function")
def qcannotators(db, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'qcannotators.json')


@pytest.fixture(scope="function")
def mock_data(db, django_db_blocker):
    # NOTE: Since this loads directly to the DB without any validation and thus call to loaddata(), no data files are
    # present. If you need actual spectral data, use ``mock_data_from_files`` below instead.
    with django_db_blocker.unblock():
        call_command('loaddata', 'test_data.json')


@pytest.fixture(scope="function")
def mock_data_from_files(request, monkeypatch, db, diseases, django_db_blocker, instruments):
    # Turn off auto annotation functionality so that it isn't always being tested.
    auto_annotate = False if getattr(request, "param", None) is None else request.param
    monkeypatch.setattr(settings, "AUTO_ANNOTATE", auto_annotate)

    meta_data_path = (DATA_PATH / "meta_data").with_suffix(UploadedFile.FileFormats.XLSX)
    spectral_file_path = (DATA_PATH / "spectral_data").with_suffix(UploadedFile.FileFormats.XLSX)
    with django_db_blocker.unblock():
        with meta_data_path.open(mode="rb") as meta_data:
            with spectral_file_path.open(mode="rb") as spectral_data:
                data_upload = UploadedFile(meta_data_file=django.core.files.File(meta_data,
                                                                                 name=meta_data_path.name),
                                           spectral_data_file=django.core.files.File(spectral_data,
                                                                                     name=spectral_file_path.name))
                data_upload.clean()
                data_upload.save()
                
 
@pytest.fixture(scope="function")               
def mock_data_from_form_and_spectral_file(request, db, django_db_blocker):
    spectral_file_path = (DATA_PATH/"sample").with_suffix(UploadedFile.FileFormats.XLSX)
    with django_db_blocker.unblock():
        with spectral_file_path.open(mode="rb") as spectral_record:
            data_input_form = DataInputForm(
                data={
                    "patient_id": "4efb03c5-27cd-4b40-82d9-c602e0ef7b80",
                    "gender": 'M',
                    "days_symptomatic": 1,
                    "patient_age": 1,
                    "spectra_measurement": 'ATR_FTIR',
                    "spectrometer": 'AGILENT_CORY_630',
                    "atr_crystal": 'ZNSE',
                    "acquisition_time": 1,
                    "n_coadditions": 32,
                    "resolution": 0,
                    "sample_type": 'PHARYNGEAL_SWAB',
                    "sample_processing": 'None',
                    "freezing_temp": 0,
                    "thawing_time": 0,
                },
                files={
                    "spectral_data": django.core.files.File(spectral_record, name=spectral_file_path.name)
                }
            )

            if not request.node.get_closest_marker("dont_validate"):
                assert data_input_form.is_valid(), data_input_form.errors.as_data()

            if not request.node.get_closest_marker("dont_save_to_db"):
                data_input_form.save_to_db()
