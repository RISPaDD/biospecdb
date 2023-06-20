from .qcfilter import QcFilter
from uploader.models import BioSample
from uploader.models import Patient as Symptoms

from typing import Callable, Union


def wrap_validate(func: Callable[Symptoms, BioSample], symptoms, sample) -> Union[bool, None]:
    try:
        return func(symptoms, sample)
    except Exception:
        # we will need to log exception here, or maybe transmit exception name to output?
        return None


class QcManager:

    def __init__(self):
        self.filters = {}

    def get_validators(self):
        return self.filters

    def register_validator(self, name: str, filter: QcFilter) -> None:
        assert(isinstance(filter, QcFilter))
        self.filters[name] = filter

    def validate(self, symptoms: Symptoms, sample: BioSample) -> bool:
        return {
            name: wrap_validate(filter.validate, symptoms, sample)
            for name, filter
            in self.filters.items()
        }
