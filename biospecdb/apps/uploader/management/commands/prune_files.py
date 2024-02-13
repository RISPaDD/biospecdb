import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from uploader.models import SpectralData, UploadedFile


class Command(BaseCommand):
    help = "Delete any and all orphaned data files."

    def add_arguments(self, parser):
        parser.add_argument("--dry_run",
                            action="store_true",
                            default=False,
                            help="Output files to be deleted but don't actually delete anything.")

    def handle(self, *args, **options):
        try:
            # Collect orphaned bulk data files.
            fs_files = set(Path(UploadedFile.UPLOAD_DIR).glob("*"))
            meta_data_files = set(x.meta_data_file.name for x in UploadedFile.objects.all())
            spectral_data_files = set(x.spectral_data_file.name for x in UploadedFile.objects.all())
            orphaned_files = fs_files - (meta_data_files | spectral_data_files)

            # Collect orphaned spectral data files.
            fs_files = set(Path(SpectralData.UPLOAD_DIR).glob("*"))
            data_files = set(x.data.name for x in SpectralData.objects.all())
            orphaned_files |= fs_files - data_files

            if not orphaned_files:
                self.stdout.write(self.style.WARNING("No orphaned files detected."))
                return

            # Delete orphaned files.
            for i, file in enumerate(orphaned_files):
                msg = f"{i + 1}/{len(orphaned_files)} files: '{file}'..."
                if options["dry_run"]:
                    self.stdout.write("(dry-run) " + msg)
                else:
                    self.stdout.write(f"Deleting {msg}")
                    try:
                        os.remove(file)
                    except FileNotFoundError:
                        continue

            if options["dry_run"]:
                self.stdout.write(self.style.SUCCESS("(dry-run) [Done] 0 files deleted"))
            else:
                self.stdout.write(self.style.SUCCESS(f"[Done] {len(orphaned_files)} files deleted"))

        except Exception as error:
            raise CommandError(f"An error occurred whilst trying to delete orphaned data files: - '{error}'")
