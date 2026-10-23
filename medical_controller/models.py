from django.db import models

from core import models as core_models
from location.models import Location
from location.models import HealthFacility
from core.models import User
from claim.models import Claim, ClaimService, ClaimServiceService, ClaimServiceItem
from django.utils import timezone as django_tz
import datetime
from program.models import Program
from django.db.models import Q
from collections import defaultdict
import re
from django.utils import timezone


class MedicalControlMission(core_models.HistoryModel):

    STATUS_IN_PROGRESS = "P"
    STATUS_COMPLETED = "C"

    STATUS_CHOICES = (
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed")
    )

    mission_code = models.CharField(
        max_length=20,
        unique=True
    )

    region = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        related_name="medical_control_missions"
    )

    district = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        related_name="medical_control_district_missions"
    )

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS
    )

    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING
    )

    json_ext = models.JSONField(
        null=True,
        blank=True
    )

    percentage_one = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageOne'
    )

    percentage_two = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageTwo'
    )

    percentage_three = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageThree'
    )

    percentage_four = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageFour'
    )

    class Meta:
        db_table = "tblMedicalControlMission"


class FilteredClaimsForMission(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="mission_health_facilities"
    )

    claim = models.ForeignKey(
        Claim,
        on_delete=models.DO_NOTHING
    )

    from_rejected_to_valuated = models.BooleanField(
        db_column='RejectedToValuated',
        blank=True,
        null=True
    )

    audit_explanation = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_column='AuditExplanation'
    )

    audited = models.BooleanField(
        db_column='Audited',
        blank=True,
        null=True
    )

    claim_category = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        db_column='ClaimCategory'
    )

    class Meta:
        db_table = "tblFilteredClaimsForMission"


class MissionHealthFacility(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="health_facilities"
    )

    health_facility = models.ForeignKey(
        HealthFacility,
        on_delete=models.DO_NOTHING
    )

    class Meta:
        db_table = "tblMedicalControlMissionHF"


class MissionActivityHistory(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="activity_mission_hf"
    )

    action = models.TextField(
        blank=True,
        null=True,
        db_column='Action'
    )

    action_date = models.DateTimeField(
        blank=True,
        null=True,
        db_column='ActionDate',
        default=django_tz.now
    )

    user = models.ForeignKey(
        User,
        db_column='userID',
        on_delete=models.DO_NOTHING
    )

    class Meta:
        db_table = "tblMissionActivityHistory"


def medical_controller_claims_report_query(user, **kwargs):
    """
    This method computes invoice for medical controller and
    sends the template data to the frontend side
    """
    def _period_part(date_str: str) -> str:
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            return date_str[:7]

    print("medical controller claims report query")
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    hflocation = kwargs.get("hflocation")

    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    location0 = kwargs.get("location0")
    location1 = kwargs.get("location1")
    location2 = kwargs.get("location2")
    hflocation = kwargs.get("hflocation")

    format = "%Y-%m-%d"

    date_from_object = datetime.datetime.strptime(date_from, format)
    date_from_str = date_from_object.strftime("%d/%m/%Y")

    date_to_object = datetime.datetime.strptime(date_to, format)
    date_to_str = date_to_object.strftime("%d/%m/%Y")

    dictGeo = {}
    dictBase = {
        "dateFrom": date_from_str,
        "dateTo": date_to_str
    }
    # If there is HealthFacility defined in the form
    if hflocation and hflocation!="0" :
        hflocationObj = HealthFacility.objects.filter(
            code=hflocation,
            validity_to__isnull=True
            ).first()
        dictBase["fosa"] = hflocationObj.name
        dictGeo['health_facility'] = hflocationObj.id

    # Get all 5 Programs
    today = datetime.datetime.now()
    programs = Program.objects.filter(
        validityDateFrom__lte=today).filter(
        Q(validityDateTo__isnull=True) | Q(validityDateTo__gte=today)
        ).exclude(code='DNB').order_by('-idProgram')[:5]

    program_ids = []
    for prg in programs:
        program_ids.append(prg)
    number = len(program_ids)
    # Complete to 5 elements if the result is less than 5
    while number < 5:
        program_ids.append(0)
        number += 1

    invoiceElemtTotal_MontantRecueTotal = 0
    invoiceElemtTotal_MtnValideTotal = 0
    invoiceElemtTotal_MontantRetabliTotal = 0
    invoiceElemtTotal_MontantRejeteTotal = 0
    AllMontnAjusteTotal = 0
    i = 1
    for program in program_ids:
        if i == 1:
            dictBase.update({
                "prestationForfaitaire" : [],
                "prestationPlafonnees" : [],
                "prestationsNonMedicales" : [],
                "invoiceElemtTotal": [],
                "Program1": program.nameProgram if program != 0 else " "
            })
        else:
            dictBase.update({
                "prestationForfaitaireProgram"+str(i): [],
                "prestationPlafonneesProgram"+str(i): [],
                "prestationsNonMedicalesProgram"+str(i) : [],
                "invoiceElemtTotalProgram"+str(i): [],
                "Program"+str(i): program.nameProgram if program != 0 else " "
            })
        ## Get All claim corresponding to parameter sent
        statusExcluded = [1, 2]
        value = program.idProgram if program != 0 else 0
        claimList = Claim.objects.exclude(
            status__in=statusExcluded
        ).filter(
            date_to__gte=date_from,
            date_to__lte=date_to,
            validity_to__isnull=True,
            program=value,
            **dictGeo
        )

        invoiceElemtList = defaultdict(dict)
        invoiceElemtTotal = defaultdict(int)
        invoiceElemtListP = []
        invoiceElemtListF = []
        invoiceElemtListS = []


        for cclaim in claimList:
            #First we calculate on each Service inside a
            claimService = ClaimService.objects.filter(
                claim = cclaim,
                status=1
            ).filter(validity_to__isnull=True)
            for claimServiceElmt in claimService:
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyValuatedV"] = 0
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"] = 0
                if claimServiceElmt.service.id not in invoiceElemtList[claimServiceElmt.service.packagetype]:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id] = defaultdict(dict)
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"] = defaultdict(int)
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qtyAudit"] = defaultdict(int)
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] = 0
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecueAudit"] = 0
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRejeteAudit"] = 0
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRetabliAudit"] = 0

                ## Define global information of each Line
                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["name"] = claimServiceElmt.service.name
                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["code"] = claimServiceElmt.service.code
                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["tarif"] = claimServiceElmt.service.price
                ## Status Valuated of Claim
                if cclaim.status==16:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['valuated'] += int(claimServiceElmt.qty_provided)
                    if claimServiceElmt.price_valuated == None :
                        claimServiceElmt.price_valuated = 0
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['sum'] += int(claimServiceElmt.qty_provided * claimServiceElmt.price_valuated)
                    invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyValuatedV"] += int(invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['valuated'])
                    invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"] += int(invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['sum'])

                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['all'] += claimServiceElmt.qty_provided
                if cclaim.audited:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qtyAudit"]['all'] += claimServiceElmt.qty_provided
                    invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyTotalAuditedV"] += int(claimServiceElmt.qty_provided)
                    # invoiceElemtTotal["QtyTotalAuditedV"] += int(claimServiceElmt.qty_provided)
                ## Specific Rules for Montant Recue (for different type of package)
                if claimServiceElmt.service.packagetype == "S":
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += claimServiceElmt.qty_provided * invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["tarif"]
                else:
                    # Desactivation du controle sur ManualPrice
                    #if claimServiceElmt.service.manualPrice == True :
                    #    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += claimServiceElmt.qty_provided * claimServiceElmt.service.price
                    #else :
                    claimSs = ClaimServiceService.objects.filter(
                        claim_service = claimServiceElmt
                    )
                    tarifLocal = 0
                    for claimSsElement in claimSs:
                        qty = claimSsElement.qty_adjusted or claimSsElement.qty_displayed
                        tarifLocal += qty * claimSsElement.price_asked
                    claimSi = ClaimServiceItem.objects.filter(
                        claim_service = claimServiceElmt
                    )
                    for claimSiElement in claimSi:
                        qty = claimSiElement.qty_adjusted or claimSiElement.qty_displayed
                        tarifLocal += qty * claimSiElement.price_asked
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += tarifLocal
                if cclaim.audited:
                    # Valeur déja calculé en fonction de si c'est simple ou pas, on utilise juste la valeur
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecueAudit"] = invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"]
                    if cclaim.audit_status == "R" and cclaim.rejection_reason:
                        invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRejeteAudit"] = invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"]
                    if cclaim.audit_status == "A" and cclaim.audit_explanation:
                        invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRetabliAudit"] = invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"]

                if claimServiceElmt.service.packagetype not in invoiceElemtTotal :
                    invoiceElemtTotal[claimServiceElmt.service.packagetype] = defaultdict(int)

                ### Sum of all line at footer of table
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyTotalV"] += int(claimServiceElmt.qty_provided)
                MtnNotValideV = 0
                if int(invoiceElemtTotal[claimServiceElmt.service.packagetype+"MontantRecueTotalV"] - invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"]) > 0:
                    MtnNotValideV = int(invoiceElemtTotal[claimServiceElmt.service.packagetype+"MontantRecueTotalV"] - invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"])
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnNotValideV"] = MtnNotValideV
                invoiceElemtTotal["QtyTotalV"] += int(claimServiceElmt.qty_provided)

            #Then we calculate on each Item inside a claim
            # claimItem = ClaimItem.objects.filter(
            #     claim = cclaim,
            #     status=1
            # )
            # for claimItemElmt in claimItem:
            #     if claimItemElmt.service.id not in invoiceElemtList[claimItemElmt.service.packagetype]:
            #         invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id] = defaultdict(int)

            #     if cclaim.status == "16":
            #         invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['valuated'] += claimItemElmt.qty_provided

            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["name"] = claimItemElmt.service.name
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["code"] = claimItemElmt.service.code
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["tarif"] = claimItemElmt.price_asked
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]["all"] += claimItemElmt.qty_provided
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["MontantRecue"] += invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['all'] * invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["tarif"]            
                
            #     if claimServiceElmt.service.packagetype not in invoiceElemtTotal :
            #         invoiceElemtTotal[claimServiceElmt.service.packagetype] = defaultdict(int)

            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"QtyTotalV"] += claimItemElmt.qty_provided
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"QtyValuatedV"] += int(invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['valuated'])
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValideV"] += invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['sum']
            #     MtnNotValideV = 0
            #     if invoiceElemtTotal[claimItemElmt.service.packagetype+"MontantRecueTotal"] - invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValide"] > 0:
            #         MtnNotValideV = invoiceElemtTotal[claimItemElmt.service.packagetype+"MontantRecueTotal"] - invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValide"]
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnNotValideV"] = MtnNotValideV
            #     invoiceElemtTotal["QtyTotalV"] += claimItemElmt.qty_provided
        
        invoiceElemtTotal["PQtyValuatedV"]=0
        invoiceElemtTotal["PMontantRecueTotalV"] = 0
        invoiceElemtTotal["PMtnNotValideV"] = 0
        invoiceElemtTotal["PMtnValideV"] = 0
        invoiceElemtTotal["FMontantRecueTotalV"] = 0
        invoiceElemtTotal["FQtyValuatedV"] = 0
        invoiceElemtTotal["FMtnNotValideV"] = 0
        invoiceElemtTotal["FMtnValideV"] = 0 
        invoiceElemtTotal["SQtyValuatedV"] = 0
        invoiceElemtTotal["SMontantRecueTotalV"] = 0
        invoiceElemtTotal["SMtnNotValideV"] = 0
        invoiceElemtTotal["SMtnValideV"] = 0

        if "PQtyTotalAuditedV" not in invoiceElemtTotal:
            invoiceElemtTotal["PQtyTotalAuditedV"] = 0
        if "PMontantAuditedTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["PMontantAuditedTotalV"] = 0
        if "PMontantRetabliTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["PMontantRetabliTotalV"] = 0
        if "PMontantRejeteTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["PMontantRejeteTotalV"] = 0
        if "PMontantAjusteTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["PMontantAjusteTotalV"] = 0
        if "SQtyTotalAuditedV" not in invoiceElemtTotal:
            invoiceElemtTotal["SQtyTotalAuditedV"] = 0
        if "FQtyTotalAuditedV" not in invoiceElemtTotal:
            invoiceElemtTotal["FQtyTotalAuditedV"] = 0
        if "SMontantAuditedTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["SMontantAuditedTotalV"] = 0
        if "FMontantAuditedTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["FMontantAuditedTotalV"] = 0
        if "FMontantRetabliTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["FMontantRetabliTotalV"] = 0
        if "SMontantRejeteTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["SMontantRejeteTotalV"] = 0
        if "FMontantRejeteTotalV" not in invoiceElemtTotal:
            invoiceElemtTotal["FMontantRejeteTotalV"] = 0
        invoiceElemtTotal["solde_ajusteP"] = 0
        invoiceElemtTotal["solde_ajusteF"] = 0
        invoiceElemtTotal["solde_ajusteS"] = 0

        for typeList,v in invoiceElemtList.items():
            
            for id in v:
                montantNonValide = 0
                # Correction des chiffres negatif : -- Si un montant est negatif ca veut dire que le montant valuated est superieur a la somme des sous-services / services
                # if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0 :
                montantNonValide = v[id]['MontantRecue'] - v[id]['qty']['sum']
                if typeList=="P":
                    invoiceElemtTotal["PMtnValideV"] += v[id]['qty']['sum']
                    invoiceElemtTotal["PQtyTotalAuditedV"] += v[id]['qtyAudit']['sum']
                    invoiceElemtTotal["PMontantAuditedTotalV"] += v[id]['MontantRecueAudit']
                    invoiceElemtTotal["PMontantRetabliTotalV"] += v[id]['MontantRetabliAudit']
                    invoiceElemtTotal["PMontantRejeteTotalV"] += v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["solde_ajusteP"] = (v[id]['qty']['sum'] + v[id]['MontantRetabliAudit']) - v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["PMontantAjusteTotalV"] += invoiceElemtTotal["solde_ajusteP"]

                    invoiceElemtListP.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(int(v[id]['qty']['all'])),
                        nbrFactureAudite = str(int(v[id]['qtyAudit']['all'])),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        mtnFactureAudite = str("{:,.0f}".format(v[id]['MontantRecueAudit'])),
                        mtnFactureRejete = str("{:,.0f}".format(v[id]['MontantRejeteAudit'])),
                        mtnFactureRetabli = str("{:,.0f}".format(v[id]['MontantRetabliAudit'])),
                        mtnFactureAjuste = str("{:,.0f}".format(invoiceElemtTotal["solde_ajusteP"])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(montantNonValide)),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))
                        ))

                    invoiceElemtTotal["PMontantRecueTotalV"] += v[id]['MontantRecue']
                    invoiceElemtTotal["PQtyValuatedV"] += v[id]['qty']['valuated']
                    PMtnNotValideV = 0
                    if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0:
                        PMtnNotValideV = v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["PMtnNotValideV"] += PMtnNotValideV

                if typeList=="F":
                    FMtnNotValideV = 0
                    if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0:
                        FMtnNotValideV = v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["FMtnNotValideV"] += FMtnNotValideV
                    invoiceElemtTotal["FMtnValideV"] += v[id]['qty']['sum']
                    invoiceElemtTotal["FQtyTotalAuditedV"] += v[id]['qtyAudit']['sum']
                    invoiceElemtTotal["FMontantAuditedTotalV"] += v[id]['MontantRecueAudit']
                    invoiceElemtTotal["FMontantRetabliTotalV"] += v[id]['MontantRetabliAudit']
                    invoiceElemtTotal["FMontantRejeteTotalV"] += v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["solde_ajusteF"] = (v[id]['qty']['sum'] + v[id]['MontantRetabliAudit']) - v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["FMontantAjusteTotalV"] += invoiceElemtTotal["solde_ajusteF"]

                    invoiceElemtListF.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(int(v[id]['qty']['all'])),
                        nbrFactureAudite = str(int(v[id]['qtyAudit']['all'])),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        mtnFactureAudite = str("{:,.0f}".format(v[id]['MontantRecueAudit'])),
                        mtnFactureRejete = str("{:,.0f}".format(v[id]['MontantRejeteAudit'])),
                        mtnFactureRetabli = str("{:,.0f}".format(v[id]['MontantRetabliAudit'])),
                        mtnFactureAjuste = str("{:,.0f}".format(invoiceElemtTotal["solde_ajusteF"])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(montantNonValide)),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))
                        ))
                    invoiceElemtTotal["FMontantRecueTotalV"] += v[id]['MontantRecue']
                    invoiceElemtTotal["FQtyValuatedV"] += v[id]['qty']['valuated']

                if typeList=="S":
                    invoiceElemtTotal["SQtyValuatedV"] += v[id]['qty']['valuated']
                    invoiceElemtTotal["SMtnNotValideV"] += v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["SMtnValideV"] += v[id]['qty']['sum']
                    invoiceElemtTotal["SQtyTotalAuditedV"] += v[id]['qtyAudit']['sum']
                    invoiceElemtTotal["SMontantAuditedTotalV"] += v[id]['MontantRecueAudit']
                    invoiceElemtTotal["SMontantRetabliTotalV"] += v[id]['MontantRetabliAudit']
                    invoiceElemtTotal["SMontantRejeteTotalV"] += v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["solde_ajusteS"] = (v[id]['qty']['sum'] + v[id]['MontantRetabliAudit']) - v[id]['MontantRejeteAudit']
                    invoiceElemtTotal["SMontantAjusteTotalV"] += invoiceElemtTotal["solde_ajusteS"]
                    invoiceElemtListS.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(int(v[id]['qty']['all'])),
                        nbrFactureAudite = str(int(v[id]['qtyAudit']['all'])),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        mtnFactureAudite = str("{:,.0f}".format(v[id]['MontantRecueAudit'])),
                        mtnFactureRejete = str("{:,.0f}".format(v[id]['MontantRejeteAudit'])),
                        mtnFactureRetabli = str("{:,.0f}".format(v[id]['MontantRetabliAudit'])),
                        mtnFactureAjuste = str("{:,.0f}".format(invoiceElemtTotal["solde_ajusteS"])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(v[id]['MontantRecue'] - v[id]['qty']['sum'])),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))
                        ))
                    invoiceElemtTotal["SMontantRecueTotalV"] += v[id]['MontantRecue']

        ## Calcaulating of each invoiceElemtTotal
        invoiceElemtTotal["NbFactureValideTotal"] = invoiceElemtTotal["FQtyValuatedV"] + invoiceElemtTotal["SQtyValuatedV"] + invoiceElemtTotal["PQtyValuatedV"]
        invoiceElemtTotal["NbFactureValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["NbFactureValideTotal"])
        invoiceElemtTotal["FQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["FQtyValuatedV"])
        invoiceElemtTotal["SQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["SQtyValuatedV"])
        invoiceElemtTotal["PQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["PQtyValuatedV"])
        invoiceElemtTotal["FQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["FQtyTotalV"])
        invoiceElemtTotal["SQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["SQtyTotalV"])
        invoiceElemtTotal["PQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["PQtyTotalV"])

        invoiceElemtTotal["FQtyTotalAudited"] = "{:,.0f}".format(invoiceElemtTotal["FQtyTotalAuditedV"])
        invoiceElemtTotal["SQtyTotalAudited"] = "{:,.0f}".format(invoiceElemtTotal["SQtyTotalAuditedV"])
        invoiceElemtTotal["PQtyTotalAudited"] = "{:,.0f}".format(invoiceElemtTotal["PQtyTotalAuditedV"])
        invoiceElemtTotal["FMontantAuditedTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantAuditedTotalV"])
        invoiceElemtTotal["SMontantAuditedTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantAuditedTotalV"])
        invoiceElemtTotal["PMontantAuditedTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantAuditedTotalV"])
        invoiceElemtTotal["FMontantRetabliTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRetabliTotalV"])
        invoiceElemtTotal["SMontantRetabliTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantRetabliTotalV"])
        invoiceElemtTotal["PMontantRetabliTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantRetabliTotalV"])
        invoiceElemtTotal["FMontantRejeteTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRejeteTotalV"])
        invoiceElemtTotal["SMontantRejeteTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantRejeteTotalV"])
        invoiceElemtTotal["PMontantRejeteTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantRejeteTotalV"])
        invoiceElemtTotal["FMontantAjusteTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantAjusteTotalV"])
        invoiceElemtTotal["SMontantAjusteTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantAjusteTotalV"])
        invoiceElemtTotal["PMontantAjusteTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantAjusteTotalV"])

        invoiceElemtTotal["MtnValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMtnValideV"]+invoiceElemtTotal["SMtnValideV"]+invoiceElemtTotal["PMtnValideV"])
        invoiceElemtTotal["QtyTotalAudited"] = "{:,.0f}".format(invoiceElemtTotal["FQtyTotalAuditedV"]+invoiceElemtTotal["SQtyTotalAuditedV"]+invoiceElemtTotal["PQtyTotalAuditedV"])
        invoiceElemtTotal["MontantRetabliTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRetabliTotalV"] + invoiceElemtTotal["SMontantRetabliTotalV"] + invoiceElemtTotal["PMontantRetabliTotalV"])
        invoiceElemtTotal["MontantRejeteTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRejeteTotalV"] + invoiceElemtTotal["SMontantRejeteTotalV"] + invoiceElemtTotal["PMontantRejeteTotalV"])
        invoiceElemtTotal["MontantAuditedTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantAuditedTotalV"] + invoiceElemtTotal["SMontantAuditedTotalV"] + invoiceElemtTotal["PMontantAuditedTotalV"])
        invoiceElemtTotal["MontantAjusteTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantAjusteTotalV"] + invoiceElemtTotal["SMontantAjusteTotalV"] + invoiceElemtTotal["PMontantAjusteTotalV"])

        invoiceElemtTotal_MtnValideTotal += invoiceElemtTotal["FMtnValideV"]+invoiceElemtTotal["SMtnValideV"]+invoiceElemtTotal["PMtnValideV"]
        invoiceElemtTotal["FMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["FMtnValideV"])
        invoiceElemtTotal["SMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["SMtnValideV"])
        invoiceElemtTotal["PMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["PMtnValideV"])
        invoiceElemtTotal["MtnNonValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMtnNotValideV"]+invoiceElemtTotal["SMtnNotValideV"]+invoiceElemtTotal["PMtnNotValideV"])
        invoiceElemtTotal["FMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["FMtnNotValideV"])
        invoiceElemtTotal["SMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["SMtnNotValideV"])
        invoiceElemtTotal["PMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["PMtnNotValideV"])

        invoiceElemtTotal["MontantRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal["PMontantRecueTotalV"]+invoiceElemtTotal["FMontantRecueTotalV"]+invoiceElemtTotal["SMontantRecueTotalV"])
        invoiceElemtTotal_MontantRecueTotal += invoiceElemtTotal["PMontantRecueTotalV"]+invoiceElemtTotal["FMontantRecueTotalV"]+invoiceElemtTotal["SMontantRecueTotalV"]
        invoiceElemtTotal_MontantRetabliTotal += invoiceElemtTotal["PMontantRetabliTotalV"]+invoiceElemtTotal["FMontantRetabliTotalV"] + invoiceElemtTotal["SMontantRetabliTotalV"]
        invoiceElemtTotal_MontantRejeteTotal += invoiceElemtTotal["PMontantRejeteTotalV"]+invoiceElemtTotal["FMontantRejeteTotalV"] + invoiceElemtTotal["SMontantRejeteTotalV"]
        AllMontnAjusteTotal += invoiceElemtTotal["SMontantAjusteTotalV"]  + invoiceElemtTotal["FMontantAjusteTotalV"] + invoiceElemtTotal["PMontantAjusteTotalV"]

        invoiceElemtTotal["PMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantRecueTotalV"])
        invoiceElemtTotal["SMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantRecueTotalV"])
        invoiceElemtTotal["FMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRecueTotalV"])

        invoiceElemtTotal["QtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["QtyTotalV"])
        # invoiceElemtTotal["QtyTotalAudited"] = "{:,.0f}".format(invoiceElemtTotal["QtyTotalAuditedV"])

        if i == 1:
            dictBase["prestationForfaitaire"] = invoiceElemtListP
            dictBase["prestationPlafonnees"] = invoiceElemtListF
            dictBase["prestationsNonMedicales"] = invoiceElemtListS
            dictBase["invoiceElemtTotal"] = invoiceElemtTotal
        else:
            dictBase["prestationForfaitaireProgram"+str(i)] = invoiceElemtListP
            dictBase["prestationPlafonneesProgram"+str(i)] = invoiceElemtListF
            dictBase["prestationsNonMedicalesProgram"+str(i)] = invoiceElemtListS
            dictBase["invoiceElemtTotalProgram"+str(i)] = invoiceElemtTotal
        i += 1
    # dictBase["invoiceElemtTotal"]["MontantRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRecueTotal)
    # dictBase["invoiceElemtTotal"]["MtnValideTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MtnValideTotal)
    dictBase["MontnRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRecueTotal)
    dictBase["AllMontnRetabliTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRetabliTotal)
    dictBase["AllMontnRejeteTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRejeteTotal)
    dictBase["AllMontnAjusteTotal"] =  "{:,.0f}".format(AllMontnAjusteTotal)
    
    dictBase["MtnValideTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MtnValideTotal)

    if location0:
        location0_str = Location.objects.filter(
            code=location0,
            validity_to__isnull=True
            ).first().name
        dictBase["region"] = location0_str

    if location1:
        location1_str = Location.objects.filter(
            code=location1,
            validity_to__isnull=True
            ).first().name
        dictBase["district"] =location1_str
    if location2:
        location2_str = Location.objects.filter(
            code=location2,
            validity_to__isnull=True
            ).first().name
        dictBase["area"] = location2_str
    # Invoice name
    hf_name = dictBase.get("fosa", "CSU")
    safe_hf_name = re.sub(r'[^\w\s-]', '', hf_name).strip().replace(' ', '_')
    period_start = _period_part(date_from)
    period_end = _period_part(date_to)
    generation_date = timezone.now().strftime('%Y-%m-%dT%H-%M-%S')
    filename = f"Facture_{safe_hf_name}_{period_start}_{period_end}_{generation_date}"
    dictBase["report_filename"] = filename

    return dictBase
