from abc import ABC, abstractmethod

from uploader.models import BioSample
from uploader.models import Patient as Symptoms


class QcFilter(ABC):

    @abstractmethod
    def validate(self, symptoms: Symptoms, sample: BioSample) -> bool:
        return False
