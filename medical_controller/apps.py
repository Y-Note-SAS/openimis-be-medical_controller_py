from django.apps import AppConfig
from django.conf import settings
import importlib
import inspect

MODULE_NAME = "medical_controller"

DEFAULT_CFG = {
    "gql_mutation_medical_controller_perms": ['112000']
}

CALCULATION_RULES = []

def read_all_calculation_rules():
    """function to read all calculation rules"""
    for name, cls in inspect.getmembers(importlib.import_module("calculation_comores.calculation_rule"), inspect.isclass):
        if 'calculation' in cls.__module__.split('.')[0]:
            CALCULATION_RULES.append(cls)
            cls.ready()

class MedicalControllerConfig(AppConfig):
    name = MODULE_NAME

    gql_mutation_medical_controller_perms = []

    def __load_config(self, cfg):
        for field in cfg:
            if hasattr(MedicalControllerConfig, field):
                setattr(MedicalControllerConfig, field, cfg[field])

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self.__load_config(cfg)
