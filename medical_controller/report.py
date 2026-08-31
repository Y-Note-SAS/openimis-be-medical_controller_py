# Claim report
from .report_template import medical_controller_claim_report
from .models import medical_controller_claims_report_query

report_definitions = [
    {
        "name": "medical_controller_claims_report",
        "engine": 0,
        "default_report": medical_controller_claim_report.template,
        "description": "Rapport audit des Factures",
        "module": "reportcsu",
        "python_query": medical_controller_claims_report_query, 
        "permission": ["112000"],
    }
]
