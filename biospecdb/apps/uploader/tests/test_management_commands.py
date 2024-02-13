from io import StringIO
from pathlib import Path

import pytest

from django.core.management import call_command

from uploader.models import UploadedFile, SpectralData


@pytest.mark.django_db(databases=["default", "bsr"])
class TestPruneFiles:

    def test_empty(self):
        out = StringIO()
        call_command("prune_files", stdout=out)
        assert "No orphaned files detected." in out.getvalue()

    @pytest.mark.parametrize(("cmd", "expected"),
                             ((("prune_files",), (0, 0)),
                              (("prune_files", "--dry_run"), (2, 10))))
    def test_core(self, mock_data_from_files, cmd, expected):
        assert len(list(Path(UploadedFile.UPLOAD_DIR).glob('*'))) == 2
        assert len(list(Path(SpectralData.UPLOAD_DIR).glob('*'))) == 10

        out = StringIO()
        call_command(*cmd, stdout=out)

        assert len(list(Path(UploadedFile.UPLOAD_DIR).glob('*'))) == expected[0]
        assert len(list(Path(SpectralData.UPLOAD_DIR).glob('*'))) == expected[1]

        out.seek(0)
        assert len(out.readlines()) == 13
