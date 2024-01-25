from inspect import signature

from django.contrib import admin
from django.db.models import Q
from django.db.utils import OperationalError
from django import forms
from nested_admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin

from biospecdb.util import to_bool
from .models import BioSample, Observable, Instrument, Patient, SpectralData, Observation, UploadedFile, Visit,\
    QCAnnotator, QCAnnotation, Center, get_center, BioSampleType, SpectraMeasurementType


class RestrictedByCenterMixin:
    """ Restrict admin access to objects belong to user's center. """
    def _has_perm(self, request, obj):
        user_center = request.user.center if request.user else None

        if (not user_center) or (obj is None):
            # Those without centers "own" all.
            return True  # security risk!?

        obj_center = get_center(obj)
        if not obj_center:
            # Objects without centers are "owned" by all.
            return True

        return obj_center == user_center

    def has_view_permission(self, request, obj=None):
        has_base_perm = super().has_view_permission(request, obj=obj)

        if obj is None or request.user.is_superuser:
            return has_base_perm

        return has_base_perm and self._has_perm(request, obj)

    def has_module_permission(self, request):
        return super().has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        # Note: The signature isn't symmetric for ``admin.ModelAdmin`` and ``admin.InlineModelAdmin`` so we introspect
        # their func signatures. Their signatures are:
        # * ``admin.ModelAdmin.has_add_permission(self, request)``
        # * ``admin.InlineModelAdmin.has_add_permission(self, request, obj=None)``
        kwargs = {"obj": obj} if "obj" in signature(super().has_add_permission).parameters else {}
        return super().has_add_permission(request, **kwargs)

    def has_change_permission(self, request, obj=None):
        has_base_perm = super().has_change_permission(request, obj=obj)

        if obj is None or request.user.is_superuser:
            return has_base_perm

        return has_base_perm and self._has_perm(request, obj)

    def has_delete_permission(self, request, obj=None):
        has_base_perm = super().has_delete_permission(request, obj)

        if obj is None or request.user.is_superuser:
            return has_base_perm

        return has_base_perm and self._has_perm(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Limit center form fields to user's center, and set initial value as such.
            Exceptions are made for superusers.
        """
        if db_field.name == "center" and request.user.center:
            kwargs["initial"] = Center.objects.get(pk=request.user.center.pk)
            if not request.user.is_superuser:
                kwargs["queryset"] = Center.objects.filter(pk=request.user.center.pk)
        elif db_field.name == "observable" and request.user.center:
            center = Center.objects.get(pk=request.user.center.pk)
            kwargs["queryset"] = Observable.objects.filter(Q(center=center) | Q(center=None))

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(BioSampleType)
admin.site.register(SpectraMeasurementType)


@admin.register(Instrument)
class InstrumentAdmin(RestrictedByCenterMixin, admin.ModelAdmin):
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    list_display = ["id", "manufacturer", "model"]
    list_filter = ("manufacturer", "model")
    ordering = ["manufacturer"]

    fieldsets = [
        (
            None,
            {
                "fields": [("id", "cid"),
                           "manufacturer",
                           "model",
                           "serial_number",
                           "center"]
            }
        ),
        (
            "Spectrometer",
            {
                "fields": ["spectrometer_manufacturer", "spectrometer_model", "spectrometer_serial_number"],
            }
        ),
        (
            "Laser",
            {
                "fields": ["laser_manufacturer", "laser_model", "laser_serial_number"],
            }
        ),
        (
            "More Details",
            {
                "classes": ["collapse"],
                "fields": [("created_at", "updated_at")],
            }
        ),
    ]


@admin.register(UploadedFile)
class UploadedFileAdmin(RestrictedByCenterMixin, admin.ModelAdmin):
    search_fields = ["created_at"]
    search_help_text = "Creation timestamp"
    list_display = ["pk", "created_at", "meta_data_file", "spectral_data_file", "center"]
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "created_at"
    ordering = ("-updated_at",)
    list_filter = ("center",)

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(center=Center.objects.get(pk=request.user.center.pk))


class QCAnnotationInline(RestrictedByCenterMixin, NestedTabularInline):
    model = QCAnnotation
    extra = 1
    min_num = 0
    show_change_link = True

    def get_extra(self, request, obj=None, **kwargs):
        # Only display inlines for those that exist, i.e., no expanded extras (if they exist).
        return 0 if obj and obj.pk and obj.qc_annotation.count() else self.extra


@admin.register(QCAnnotation)
class QCAnnotationAdmin(RestrictedByCenterMixin, admin.ModelAdmin):
    search_fields = ["annotator__name",
                     "spectral_data__bio_sample__visit__patient__patient_id",
                     "spectral_data__bio_sample__visit__patient__patient_cid"]
    search_help_text = "Annotator Name, Patient ID or CID"
    readonly_fields = ("value", "created_at", "updated_at")  # TODO: Might need specific user group for timestamps.
    list_display = ["annotator_name", "value", "annotator_value_type", "updated_at"]
    ordering = ("-updated_at",)
    list_filter = ("spectral_data__bio_sample__visit__patient__center", "annotator__name")

    @admin.display
    def annotator_name(self, obj):
        return obj.annotator.name

    @admin.display
    def annotator_value_type(self, obj):
        return obj.annotator.value_type

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        center = Center.objects.get(pk=request.user.center.pk)
        return qs.filter(spectral_data__bio_sample__visit__patient__center=center)


@admin.register(QCAnnotator)
class QCAnnotatorAdmin(RestrictedByCenterMixin, admin.ModelAdmin):
    search_fields = ["name"]
    search_help_text = "Name"
    # TODO: Might need specific user group for timestamps.)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)
    list_display = ["name", "fully_qualified_class_name", "default", "value_type"]


@admin.register(Observable)
class ObservableAdmin(RestrictedByCenterMixin, NestedModelAdmin):
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    ordering = ["name"]
    search_fields = ["name"]
    search_help_text = "Observable name"
    list_filter = ("center", "category", "value_class")
    list_display = ["name", "description", "category", "observation_count"]

    @admin.display
    def observation_count(self, obj):
        return len(obj.observation.all())

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(center=Center.objects.get(pk=request.user.center.pk)) | Q(center=None))


class ObservationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Only auto-populate "global" observables, i.e., those not related to a center (center=null).
            query = Q(center=None)
            if hasattr(self, "verbose_name"):  # Only Inline admins have verbose names.
                query &= Q(category=self.verbose_name.upper())
            kwargs = {"observables": iter(Observable.objects.filter(query))}
        except OperationalError:
            kwargs = {}
        self.form = type("NewObservationForm", (ObservationInlineForm,), kwargs)

    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    ordering = ("-updated_at",)

    fieldsets = [
        (
            None,
            {
                "fields": ["visit",
                           "observable",
                           "observable_value"]
            }
        ),
        (
            "More details",
            {
                "classes": ["collapse"],
                "fields": ["days_observed",
                           ("created_at", "updated_at")]
            }
        )
    ]

    @admin.display
    def patient_id(self, obj):
        return obj.visit.patient.patient_id

    @admin.display
    def observable_name(self, obj):
        return obj.observable.name

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(visit__patient__center=Center.objects.get(pk=request.user.center.pk))


class ObservationInlineForm(forms.ModelForm):
    observables = iter([])

    @staticmethod
    def _get_widget(value_class):
        value_class = Observable.Types(value_class)
        if value_class is Observable.Types.BOOL:
            widget = forms.CheckboxInput(check_test=to_bool)
        elif value_class is Observable.Types.FLOAT:
            widget = forms.NumberInput()
        elif value_class is Observable.Types.INT:
            widget = forms.NumberInput()
        elif value_class is Observable.Types.STR:
            widget = forms.TextInput()
        else:
            raise NotImplementedError(f"Dev error: missing widget mapping for type '{value_class}'.")
        return widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            observable = next(self.observables)
            self.fields["observable"].initial = observable
            self.fields["observable_value"].widget = self._get_widget(observable.value_class)
        except StopIteration:
            pass


class ObservationInline(ObservationMixin, RestrictedByCenterMixin, NestedTabularInline):
    extra = 0
    model = Observation
    show_change_link = True
    fk_name = "visit"

    # Override fieldsets from ObservationMixin as fields & fieldsets cannot both be set.
    fieldsets = None
    fields = ["observable", "observable_value"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Limit observable to user's center (super's functionality) and admin category. """
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "observable":
            field.queryset = Observable.objects.filter(category=self.verbose_name.upper())
        return field

    def get_queryset(self, request):
        """ Limit observable to user's center and admin category. """
        qs = super().get_queryset(request)
        center = Center.objects.get(pk=request.user.center.pk)
        query = Q(observable__category=self.verbose_name.upper()) & \
            (Q(visit__patient__center=center) | Q(visit__patient__center=None))
        return qs.filter(query)

    def get_extra(self, request, obj=None, **kwargs):
        """ Only list extra inline forms when no data exists, i.e., new patient form. """
        if obj and obj.pk and obj.observation.count():
            # Only display inlines for those that exist, i.e., no extras (when self.extra=0).
            extra = self.extra
        else:
            # Note: Calling ``len(self.formfield_for_foreignkey(db_field, request)`` would be better, however, it's not
            # clear how to correctly pass ``db_field``. The following was copied from
            # ``RestrictedByCenterMixin.formfield_for_foreignkey``.
            center = Center.objects.get(pk=request.user.center.pk)
            query = Q(category=self.verbose_name.upper()) & (Q(center=center) | Q(center=None))
            extra = Observable.objects.filter(query).count()

        return extra

    @classmethod
    def factory(cls):
        return [type(f"{x}ObservationInline", (cls,), dict(verbose_name=x.lower(),
                                                           verbose_name_plural=x.lower())) for x in Observable.Category]


@admin.register(Observation)
class ObservationAdmin(ObservationMixin, RestrictedByCenterMixin, NestedModelAdmin):
    search_fields = ["observable__name", "visit__patient__patient_id", "visit__patient__patient_cid"]
    search_help_text = "Observable, Patient ID or CID"
    date_hierarchy = "updated_at"
    list_filter = ("visit__patient__center", "observable__category", "visit__patient__gender", "observable")
    list_display = ["patient_id", "observable_name", "visit"]


class SpectralDataMixin:
    ordering = ("-updated_at",)
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            None,
            {
                "fields": ["instrument", "bio_sample", "data"]
            }
        ),
        (
            "Measurement Details",
            {
                "fields": ["measurement_id",
                           "measurement_type",
                           "atr_crystal",
                           "n_coadditions",
                           "acquisition_time",
                           "resolution",
                           "power",
                           "temperature",
                           "pressure",
                           "humidity",
                           "date"],
            }
        ),
        (
            "SERS Details",
            {
                "classes": ["collapse"],
                "fields": ["sers_description",
                           "sers_particle_material",
                           "sers_particle_size",
                           "sers_particle_concentration"],
            }
        ),
        (
            "More Details",
            {
                "classes": ["collapse"],
                "fields": ["id", ("created_at", "updated_at")],
            }
        ),
    ]

    @admin.display
    def patient_id(self, obj):
        return obj.bio_sample.visit.patient_id

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(bio_sample__visit__patient__center=Center.objects.get(pk=request.user.center.pk))


@admin.register(SpectralData)
class SpectralDataAdmin(SpectralDataMixin, RestrictedByCenterMixin, NestedModelAdmin):
    search_fields = ["bio_sample__visit__patient__patient_id", "bio_sample__visit__patient__patient_cid"]
    search_help_text = "Patient ID or CID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    list_display = ["patient_id", "instrument", "data"]
    list_filter = ("bio_sample__visit__patient__center",
                   "instrument",
                   "measurement_type",
                   "bio_sample__sample_type",
                   "bio_sample__sample_processing",
                   "bio_sample__visit__patient__gender")


class SpectralDataAdminWithInlines(SpectralDataAdmin):
    inlines = [QCAnnotationInline]


class SpectralDataInline(SpectralDataMixin, RestrictedByCenterMixin, NestedStackedInline):
    model = SpectralData
    extra = 1
    min_num = 0
    show_change_link = True
    fk_name = "bio_sample"

    def get_extra(self, request, obj=None, **kwargs):
        # Only display inlines for those that exist, i.e., no expanded extras (if they exist).
        return 0 if obj and obj.pk and obj.spectral_data.count() else self.extra


class BioSampleMixin:
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    ordering = ("-updated_at",)

    @admin.display
    def patient_id(self, obj):
        return obj.visit.patient_id

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(visit__patient__center=Center.objects.get(pk=request.user.center.pk))


@admin.register(BioSample)
class BioSampleAdmin(BioSampleMixin, RestrictedByCenterMixin, NestedModelAdmin):
    search_fields = ["visit__patient__patient_id", "visit__patient__patient_cid"]
    search_help_text = "Patient ID or CID"
    date_hierarchy = "updated_at"
    list_filter = ("visit__patient__center", "sample_type", "sample_processing")
    list_display = ["patient_id", "sample_type"]


class BioSampleAdminWithInlines(BioSampleAdmin):
    inlines = [SpectralDataInline]


class BioSampleInline(BioSampleMixin, RestrictedByCenterMixin, NestedStackedInline):
    model = BioSample
    extra = 1
    min_num = 0
    show_change_link = True
    fk_name = "visit"
    inlines = [SpectralDataInline]

    def get_extra(self, request, obj=None, **kwargs):
        # Only display inlines for those that exist, i.e., no expanded extras (if they exist).
        return 0 if obj and obj.pk and obj.bio_sample.count() else self.extra


class VisitAdminMixin:
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    ordering = ("-updated_at",)

    fieldsets = [
        (
            None,
            {
                "fields": ["patient", "patient_age", "days_observed"]
            }
        ),
        (
            "Advanced",
            {
                "classes": ["collapse"],
                "fields": ["previous_visit"],
            }
        ),
    ]

    @admin.display
    def patient_id(self, obj):
        return obj.patient.patient_id

    @admin.display
    def visit_count(self, obj):
        return Visit.objects.filter(patient=obj.patient).count()

    @admin.display
    def gender(self, obj):
        return obj.patient.gender

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(patient__center=Center.objects.get(pk=request.user.center.pk))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Limit previous_visit to user's center (super's functionality) and admin category. """
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "previous_visit":
            visit_pk = request.resolver_match.kwargs.get("object_id", None)
            visit = Visit.objects.get(pk=visit_pk) if visit_pk else None
            patient = visit.patient if visit else None

            # Note: Our forms aren't dynamic and thus this still won't solve the situation where a new visit is
            #       added, a patient selected AND then have the previous_visit selection reduced based on the selected
            #       patient. The form knows nothing about the selected patient until posted.

            if patient:
                field.queryset = Visit.objects.filter(patient=patient).exclude(pk=visit_pk)
            else:
                if request.user.is_superuser:
                    field.queryset = Visit.objects.all()
                else:
                    field.queryset = Visit.objects.filter(patient__center=Center.objects.get(pk=request.user.center.pk))
        return field


class VisitInline(VisitAdminMixin, RestrictedByCenterMixin, NestedTabularInline):
    model = Visit
    extra = 1
    min_num = 0
    show_change_link = True
    fk_name = "patient"
    inlines = [BioSampleInline, *ObservationInline.factory()]

    def get_extra(self, request, obj=None, **kwargs):
        # Only display inlines for those that exist, i.e., no expanded extras (if they exist).
        return 0 if obj and obj.pk and obj.visit.count() else self.extra


@admin.register(Visit)
class VisitAdmin(VisitAdminMixin, RestrictedByCenterMixin, NestedModelAdmin):
    search_fields = ["patient__patient_id", "patient__patient_cid"]
    search_help_text = "Patient ID or CID"
    date_hierarchy = "updated_at"
    list_filter = ("patient__center",)
    # autocomplete_fields = ["previous_visit"]  # Conflicts with VisitAdminForm queryset.
    list_display = ["patient_id", "visit_count", "gender"]


class VisitAdminWithInlines(VisitAdmin):
    inlines = [BioSampleInline, *ObservationInline.factory()]


@admin.register(Patient)
class PatientAdmin(RestrictedByCenterMixin, NestedModelAdmin):
    search_fields = ["patient_id", "patient_cid"]
    search_help_text = "Patient ID or CID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_filter = ("center", "gender")
    list_display = ["patient_id", "patient_cid", "gender", "age", "visit_count", "center"]

    @admin.display
    def age(self, obj):
        age = 0
        for visit in obj.visit.all():
            age = max(age, visit.patient_age)
        return age

    @admin.display
    def visit_count(self, obj):
        return len(obj.visit.all())

    def get_queryset(self, request):
        """ List only objects belonging to user's center. """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(center=Center.objects.get(pk=request.user.center.pk))


class PatientAdminWithInlines(PatientAdmin):
    inlines = [VisitInline]


# NOTE: The following admin can be used to visually sanity check that changes by user.models.Center to the "default" DB
# get reflected in the "bsr" DB. We never want uploader.models.Center to be editable by any admin page, so we restrict
# access below even if this is never used. Admin functionality belong to the admin page for ``user.models.Center``.
# @admin.register(Center)
# class CenterAdmin(admin.ModelAdmin):
#     fields = ("name", "country", "id")
#     list_display = ("name", "country")
#     readonly_fields = ("name", "country", "id")
#
#     def has_view_permission(self, request, obj=None):
#         return request.user.is_superuser
#
#     def has_module_permission(self, request):
#         return request.user.is_superuser
#
#     def has_add_permission(self, request):
#         return False
#
#     def has_change_permission(self, request, obj=None):
#         return False
#
#     def has_delete_permission(self, request, obj=None):
#         return False


class DataAdminSite(admin.AdminSite):
    site_header = "Biosample Spectral Repository"
    index_title = "Data Administration"
    site_title = index_title

    model_order = [Patient,
                   Visit,
                   Observation,
                   BioSample,
                   SpectralData,
                   UploadedFile
                   ]

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)

        if hasattr(self, "model_order"):
            for app in app_list:
                app["models"].sort(key=lambda x: self.model_order.index(x["model"]))

        return app_list


data_admin = DataAdminSite(name="data_admin")
data_admin.register(Patient, admin_class=PatientAdminWithInlines)
data_admin.register(Visit, admin_class=VisitAdminWithInlines)
data_admin.register(Observation, admin_class=ObservationAdmin)
data_admin.register(BioSample, admin_class=BioSampleAdminWithInlines)
data_admin.register(SpectralData, admin_class=SpectralDataAdminWithInlines)
data_admin.register(UploadedFile, admin_class=UploadedFileAdmin)
# data_admin.register(Instrument, admin_class=InstrumentAdmin)
# data_admin.register(QCAnnotation, admin_class=QCAnnotationAdmin)
# data_admin.register(QCAnnotator, admin_class=QCAnnotatorAdmin)
# data_admin.register(Observable, admin_class=ObservableAdmin)
