from abc import ABC, abstractmethod


# just a stub emulating data model class
class Symptoms:
    pass


# just a stub emulating data model class
class BioSample:
    pass


class QcFilter(ABC):

    @abstractmethod
    def validate(self, symptoms: Symptoms, sample: BioSample) -> bool:
        return False
