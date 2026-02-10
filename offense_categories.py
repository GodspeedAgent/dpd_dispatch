"""
Offense categorization and semantic search for Dallas Police incidents.

Provides mappings and utilities for categorizing the 300+ unique offense types
from the Police Incidents dataset into semantic categories for easier analysis.
"""

from typing import Dict, List, Set, Optional
from enum import Enum


class OffenseCategory(str, Enum):
    """High-level offense categories for semantic searching."""
    VIOLENT = "violent"
    PROPERTY = "property"
    DRUG = "drug"
    WEAPON = "weapon"
    VEHICLE = "vehicle"
    SEX_CRIME = "sex_crime"
    FRAUD = "fraud"
    ASSAULT = "assault"
    THEFT = "theft"
    BURGLARY = "burglary"
    ROBBERY = "robbery"
    TRAFFIC = "traffic"
    PUBLIC_ORDER = "public_order"
    DEATH = "death"
    ANIMAL = "animal"
    OTHER = "other"


# Keyword mappings for semantic search
OFFENSE_KEYWORDS = {
    OffenseCategory.WEAPON: {
        'gun', 'firearm', 'weapon', 'discharge', 'deadly conduct', 
        'unlawful carrying', 'prohibited weapon'
    },
    OffenseCategory.SEX_CRIME: {
        'sex', 'sexual', 'rape', 'assault (sex)', 'indecency',
        'prostitution', 'trafficking'
    },
    OffenseCategory.DRUG: {
        'drug', 'marijuana', 'cont sub', 'poss', 'delivery',
        'man del', 'pen grp', 'paraphernalia', 'prescription'
    },
    OffenseCategory.ASSAULT: {
        'assault', 'bodily injury', 'deadly weapon', 'serious bodily',
        'family violence', 'offensive contact'
    },
    OffenseCategory.THEFT: {
        'theft', 'shoplifting', 'shoplift', 'theft from', 'theft of prop',
        'theft from person', 'pickpocket', 'purse snatch', 'unauthorized use'
    },
    OffenseCategory.BURGLARY: {
        'burglary', 'bmv', 'breaking and entering', 'forced entry',
        'no forced entry', 'habitation', 'building'
    },
    OffenseCategory.ROBBERY: {
        'robbery', 'robbery of', 'robbery (agg)'
    },
    OffenseCategory.VEHICLE: {
        'motor veh', 'automobile', 'truck', 'bmv', 'unauthorized use',
        'stolen vehicle', 'auto theft'
    },
    OffenseCategory.FRAUD: {
        'fraud', 'forgery', 'deception', 'identity', 'credit card',
        'debit card', 'false statement', 'identifying info'
    },
    OffenseCategory.TRAFFIC: {
        'dwi', 'traffic', 'traf vio', 'driving', 'duty on strike',
        'reckless', 'evading', 'racing', 'accident'
    },
    OffenseCategory.DEATH: {
        'murder', 'death', 'homicide', 'manslaughter', 'fatality'
    },
    OffenseCategory.ANIMAL: {
        'dog', 'animal', 'cruelty', 'livestock', 'bite'
    },
    OffenseCategory.PUBLIC_ORDER: {
        'public intoxication', 'disorderly', 'trespass', 'harassment',
        'terroristic threat', 'threat', 'stalking', 'gambling'
    },
}


# Detailed offense type mappings (based on actual data)
OFFENSE_TYPE_MAP = {
    # Violent crimes
    OffenseCategory.VIOLENT: [
        'MURDER',
        'ASSAULT (AGG) -SERIOUS BODILY INJURY',
        'ASSAULT (AGG) -DEADLY WEAPON',
        'ASSAULT (AGG) -DISCH FIREARM  OCC BLDG/HOUSE/VEH (AGG)',
        'ASSAULT (AGG) -RETALIATION (AGG)',
        'ASSAULT (AGG) -AGAINST SECURITY OFF (AGG)',
        'KIDNAPPING - PRELIMINARY INVESTIGATION',
        'ARSON -SINGLE RESIDENCE INHABITED',
        'ARSON -ALL OTHER STRUCTURES - INHABITED',
        'ARSON -COMMUNITY/PUBLIC - UNINHABITED',
        'ARSON -SINGLE RESIDENCE UNINHABITED',
    ],
    
    # Assault (all types)
    OffenseCategory.ASSAULT: [
        'ASSAULT -BODILY INJURY ONLY',
        'ASSAULT -VERBAL THREAT',
        'ASSAULT -OF SECURITY OFFICER - BODILY INJURY ONLY',
        'ASSAULT -PUB SERV (LAW ENF) - BODILY INJURY ONLY',
        'ASSAULT -PUB SERV (NON LAW ENF) - BODILY INJURY ONLY',
        'ASSAULT -ELD OR DISABLED VIC -BODILY INJURY ONLY',
        'ASSAULT -ELD OR DISABLED VIC -OFFENSIVE CONTACT',
        'ASSAULT - PRELIMINARY INVESTIGATION *NON FAMILY VIOLENCE',
        'ASSAULT (AGG) - PRELIMINARY INVESTIGATION *NON FAMILY VIOLENCE',
        'INTOXICATION ASSAULT W/VEH SERIOUS BODILY INJURY',
    ],
    
    # Robbery
    OffenseCategory.ROBBERY: [
        'ROBBERY OF BUSINESS',
        'ROBBERY OF INDIVIDUAL',
        'ROBBERY OF INDIVIDUAL (AGG)',
        'ROBBERY OF BUSINESS (AGG)',
        'ROBBERY OF INDIVIDUAL - PRELIMINARY INVESTIGATION',
        'ROBBERY (AGG) OF INDIVIDUAL, PRELIMINARY INVESTIGATION',
    ],
    
    # Theft
    OffenseCategory.THEFT: [
        'THEFT - PRELIMINARY INVESTIGATION',
        'THEFT OF PROP > OR EQUAL $750 <$2,500 (NOT SHOPLIFT) PC31.03(e3)',
        'THEFT OF PROP > OR EQUAL $100 <$750 (NOT SHOPLIFT) PC31.03(e2A)',
        'THEFT OF PROP (AUTO ACC) > OR EQUAL $750 <$2,500 (NOT EMP) PC31.03 (e3)',
        'THEFT OF PROP (AUTO ACC) > OR EQUAL $100 BUT<$750(NOT EMP',
        'THEFT OF PROP > OR EQUAL $2,500 <$30K (NOT SHOPLIFT) PC31.03(e4A)',
        'THEFT OF PROP > OR EQUAL $100 <$750 (EMPLOYEE) PC31.03(e2A)',
        'THEFT OF PROP (AUTO ACC) <$50 - (NOT EMP)',
        'THEFT OF PROP <$100 -SHOPLIFTING - (NOT BY EMPLOYEE)',
        'THEFT FROM BUILDING> OR EQUAL $750<$2500 (NOT SHOPLIFT)',
        'THEFT FROM PERSON',
        'THEFT OF PROP > OR EQUAL $750 BUT <$2,500 (NOT SHOPLIFT)',
        'THEFT OF PROP <$100 - OTHER THAN SHOPLIFT',
        'THEFT OF SERVICE < $100',
        'THEFT FROM PERSON-PICKPOCKE',
        'THEFT OF FIREARM',
        'THEFT FROM PERSON-PURSE SNATC',
        'THEFT FROM PERSON (ATT) PICKPOCKET',
        'THEFT OF SERVICE > OR EQUAL $500 BUT <$1,500',
        'THEFT BY DECEPTION (FRAUD) >OR EQUAL $100 <$750',
        'THEFT OF MATERIAL 50% ALUM/BRNZE/COPPER <$20K',
        'THEFT OF SERVICE > OR EQUAL $100 BUT <$750',
        'THEFT OF SERVICE > OR EQUAL $20 BUT <$500',
        'THEFT OF SERVICE < $20',
        'THEFT OF CATTLE/HORSE/EXOTIC LIVESTOCK <$150K PC31.03(e5A)',
        'THEFT ORG RETAIL -(NOT EMP)> $1500<$20,000',
        'POSSESSION OF STOLEN PROPERTY',
    ],
    
    # Burglary & Breaking/Entering
    OffenseCategory.BURGLARY: [
        'BURGLARY OF HABITATION -NO FORCED ENTRY',
        'BMV',
        'BURGLARY OF BUILDING - FORCED ENTRY',
        'BURGLARY OF HABITATION - FORCED ENTRY',
        'BURGLARY OF BUILDING - NO FORCED ENTRY',
        'BMV <$1,500  2/MORE PREV CONV- (NOT EMPLOYEE)',
        'BURGLARY OF HABITATION (ATT)',
        'BURGLARY - PRELIMINARY INVESTIGATION',
        'BURGLARY OF A COIN OPERATED MACHINE',
        'BMV - PRELIMINARY INVESTIGATION',
        'BMV (OF AUTO ACCESSORY) (P.C. 30.04(A))',
        'BMV (ATT)',
    ],
    
    # Vehicle crimes
    OffenseCategory.VEHICLE: [
        'UNAUTHORIZED USE OF MOTOR VEH - AUTOMOBILE',
        'UNAUTHORIZED USE OF MOTOR VEH - (ATT) TRUCK OR BUS',
        'UNAUTHORIZED USE OF MOTOR VEH - (ATT) AUTOMOBILE',
        'RECOVERED OUT OF TOWN STOLEN VEHICLE (NO OFFENSE)',
        'UNAUTHORIZED USE OF MOTOR VEH - TRUCK OR BUS',
        'UNAUTHORIZED USE OF MOTOR VEH - OTHER VEH',
        'UNAUTHORIZED USE OF MOTOR VEH - (ATT) OTHER VEH',
        'UNAUTHORIZED USE OF MOTOR VEH - PRELIMINARY INVEST',
    ],
    
    # Drug offenses
    OffenseCategory.DRUG: [
        'POSS CONT SUB PEN GRP 1 <1G',
        'POSS CONT SUB PEN GRP 2 > OR EQUAL  1G<4G',
        'POSS MARIJUANA <2OZ',
        'POSS CONT SUB PEN GRP 3 < 28G',
        'MAN DEL CONT SUB PEN GRP 1 > OR EQUAL 4G<200G',
        'MAN DEL CONT SUB PEN GRP 1 > OR EQUAL 1G<4G',
        'MAN DEL CONT SUB PEN GRP 1 <1G',
        'POSS CONT SUB PEN GRP 1 > OR EQUAL 1G<4G',
        'POSSESSION OF DRUG PARAPHERNALIA',
        'POSS MARIJUANA >2OZ< OR EQUAL 4OZ *DRUG FREE ZONE*',
        'POSS MARIJUANA >4OZ< OR EQUAL 5LBS',
        'POSS CONT SUB PEN GRP 2 < 1G',
        'POSS CONT SUB PEN GRP 2-A < OR EQUAL 2 OZ',
        'POSS OF DANGEROUS DRUG',
        'POSS MARIJUANA <2OZ *DRUG FREE ZONE*',
        'POSS CONT SUB PEN GRP 4 > OR EQUAL 28G<200G',
        'POSS CONT SUB PEN GRP 1 > OR EQUAL 4G<200G',
        'POSS CONT SUB NOT IN PEN GRP',
        'POSS CONT SUB PEN GRP 1 >1G *DRUG FREE ZONE*',
        'MAN DEL CONT SUB PEN GRP 3/4 <28G',
        'DELIVERY MARIJUANA < OR EQUAL 1/4 OZ',
        'DELIVERY MARIJUANA >1/4 OZ< OR EQUAL 5LBS *DRUG FREE ZONE*',
        'DELIVERY MARIJUANA < OR EQUAL 1/4 OZ REMUN *DRUG FREE ZONE*',
        'FORGING OR ALTERING PRESCRIPTION',
        'FRAUD DELIVERS PRESCRIPTION FORMS SCHEDULE LLL,LV,V',
    ],
    
    # Weapon offenses
    OffenseCategory.WEAPON: [
        'UNLAWFUL CARRYING WEAPON',
        'DISCHARGE FIREARM IN CERTAIN MUNICIPALITIES',
        'UNLAWFUL POSS FIREARM BY FELON',
        'UNLAWFUL CARRYING WEAPON PROHIBITED PLACES',
        'DEADLY CONDUCT',
        'DEADLY CONDUCT DISCHARGE FIREARM',
        'DEADLY CONDUCT-PRELIMINARY INVESTIGATION',
        'DEADLY CONDUCT DISCHARGE FIREARM (ASSAULT)',
        'UNLAWFUL POSS METAL OR BODY ARMOR BY FELON',
        'PROHIBITED WEAPON PC',
        'DISORDERLY CONDUCT DISCHARGE/DISPLAY FIREARM',
        'TAKE WEAPON FROM AN OFFICER (ATT)',
    ],
    
    # Fraud & Identity crimes
    OffenseCategory.FRAUD: [
        'FRAUD USE/POSS IDENTIFYING INFO-PRELIMINARY INVESTIGATION',
        'CREDIT CARD OR DEBIT CARD ABUSE - PRELIMINARY INVESTIGATION',
        'FORGERY FINANCIAL INSTRUMENT',
        'FRAUD USE/POSS IDENTIFYING INFO # ITEMS < 5',
        'CREDIT CARD OR DEBIT CARD ABUSE',
        'FORGERY TO DEFRAUD OR HARM OF ANOTHER',
        'FORGERY- PRELIMINARY INVESTIGATION',
        'THEFT BY DECEPTION (FRAUD) >OR EQUAL $750 <$2500',
        'THEFT BY DECEPTION (FRAUD) >OR EQUAL $2500 <$30K',
        'FALSE STATEMENT FOR PROPERTY/CREDIT > $30K < $150K PC32.32(c5)',
        'FALSE STATEMENT FOR PROPERTY/CREDIT> $2,500 < $30K PC32.32(c4)',
        'FRAUD USE/POSS IDENTIFYING INFO # ITEMS 10<50',
        'FRAUD USE/POSS IDENTIFYING INFO # ITEMS 5<10',
        'FRAUD USE/POSS IDENT INFO # ITEMS <5 ELDERLY',
        'FRAUD EXPLOITATION OF CHILD/ELDERLY/DISABLED( PC 32.53(c))',
        'FORGERY TO DEFRAUD OR HARM ELDERLY',
        'FORGERY GOVT/NATIONAL INST/MONEY/SECURITY',
    ],
    
    # Traffic violations
    OffenseCategory.TRAFFIC: [
        'TRAF VIO -DUTY ON STRIKE UNATTENDED VEH > OR EQUAL $200',
        'TRAF VIO -DUTY ON STRIKE FIX/HWY LANDSCAPE > OR EQUAL $200 TC 550.025(b)2',
        'TRAF VIO - DUTY ON STRIKE UNATTENDED (PARKED) VEHICLE >$200 DAMAGE',
        'EVADING ARREST DETENTION W/VEHICLE PC38.04(b)(2)(A)',
        'DWI 1 PREV CONV',
        'ACCIDENT INVOLVING INJURY',
        'DWI',
        'TRAFFIC VIOLATION - NON HAZARDOUS',
        'DWI BAC > OR EQUAL TO 0.15',
        'DWI W/OPEN CONTAINER',
        'DUTY ON STRIKE UNATTENDED (PARKED) VEHICLE',
        'TRAF VIO -DRIV W/OUT LIC INV W/PREV CONV/SUSP/W/O FIN RES',
        'TRAFFIC VIOLATION - HAZARDOUS',
        'TRAF VIO - DUTY ON STRIKE FIXTURE/HWY LANDSCAPE> OR EQUAL $200',
        'TRAF VIO - DUTY ON STRIKE FIXTURE/HWY LANDSCAPE< $200',
        'TRAF VIO -DUTY ON STRIKE UNATTENDED VEH < $200',
        'TRAF VIO -RECKLESS DRIVING',
        'FAIL TO LEAVE ID AT SCENE OF ACCIDENT DAMAGE < $200',
        'DWI 2 OR MORE PREV CONV',
        'TRAF VIO -RACING ON HIGHWAY CAUSING BODILY INJURY',
        'TRAF VIO -OPERATE MOTOR VEH W/O FIN RESP',
        'TRAF VIO -MAKE/POSS CFT INSP RPT/INS DOC INTD HARM/DEFRAUD',
        'TRAF VIO - DUTY ON STRIKE UNATTENDED (PARKED) VEHICLE< $200 DAMAG',
        'ACCIDENT INV DAMAGE TO VEHICLE <$200',
        'TRAF VIO - DUTY ON STRIKE UNATTENDED (PARKED) VEHICLE',
        'TRAF VIO - DUTY ON STRIKING UNATTENDED VEH',
        'TRAFFIC FATALITY- NOT DWI- UNINTENTIONAL (NO OFFENSE)',
    ],
    
    # Property damage
    OffenseCategory.PROPERTY: [
        'CRIM MISCHIEF > OR EQUAL $100 < $750',
        'CRIM MISCHIEF > OR EQUAL $1,500 BUT < $20K',
        'CRIM MISCHIEF <$100',
        'CRIM MISCHIEF >OR EQUAL $2,500 BUT <$30K',
        'CRIM MISCHIEF > OR EQUAL $50 BUT < $500',
        'CRIM MISCHIEF >OR EQUAL $750 < $2,500',
        'CRIM MISCHIEF > OR EQUAL $500 BUT < $1,500',
        'CRIM MISCHIEF > OR EQUAL $2,500 < $30K',
        'RECKLESS DAMAGE',
        'CRIM MISCHIEF -PRELIMINARY INVESTIGATION',
        'CRIM MISCHIEF >OR EQUAL $100 BUT <$750',
        'CRIM MISCHIEF >OR EQUAL $750 BUT <$2,500',
        'CRIM MISCHIEF <$1500 HABITATION FA/EXPLOS',
        'CRIM MISCHIEF < $50',
        'CRIM MISCHIEF IMPAIR/INTERRUPT PUB SERVICE',
        'GRAFFITI PECUNIARY LOSS > OR EQUAL $2500 <$30K PC28.08(b4)',
        'GRAFFITI PECUNIARY LOSS <$1500',
        'TAMPER W/IDENTIFICATION NUMBERS PERSONAL PROBERTY',
        'TAMPER W/IDENTIFICATION NUMBERS PERSONAL PROPERTY',
        'TAMPER W/CONSUMER PRODUCT  NO INJUR',
        'TAMPER FABRICATE PHYSICAL EVID WITH INTENT TO IMPAIR',
    ],
    
    # Public order
    OffenseCategory.PUBLIC_ORDER: [
        'PUBLIC INTOXICATION',
        'HARASSMENT-REPEATED ELECTRONIC COMMUNICATION',
        'OPEN BUILDING (NO OFFENSE)',
        'THREATENING PHONE CALLS',
        'CRIMINAL TRESPASS WARNING',
        'CRIMINAL TRESPASS',
        'RESIST ARREST SEARCH OR TRANSPORT',
        'CRIMINAL TRESPASS AFFIDAVIT',
        'OBSTRUCTION OR RETALIATION',
        'DISORDERLY CONDUCT',
        'STALKING',
        'HARASSMENT',
        'HARASSMENT -PRELIMINARY INVESTIGATION',
        'KEEPING A GAMBLING PLACE',
        'CRIMINAL TRESPASS HABIT/SHLTR/SUPRFUND/INFSTRT',
        'TERRORISTIC THREAT - FEAR IMMINENT SBI',
        'TERRORISTIC THREAT FEAR IMMINENT SBI',
        'TERRORISTIC THREAT -PRELIMINARY INVESTIGATION',
        'INTERFERE W/ CHILD CUSTODY',
        'INTERFERE W/EMERGENCY CALL',
        'VIO BOND/PROTECTIVE ORDER',
        'VIO BOND/PROTECTIVE ORDER ASSAULT/STALKING',
        'CRIMINAL TRESPASS HAB/DEADLY WEAP/INFRASTRUC',
        'HARASSMENT-REPEATED ELECTRONIC COMM <18 INTENT SUICIDE OR SBI',
        'UNLAWFUL DISCLOSURE OR PROMOTION OF INTIMATE VISUAL MATERIAL',
        'IMPERSONATE PUBLIC SERVANT',
        'ILLEGAL DUMPING >OR EQ 500LBS<1000LBS >OR EQ 100CFT<200CFT HSC 365.012 (f)(1)',
        'ILLEGAL DUMPING LT LIT/WASTE <500LBS OR <100 CFT HSC 365.012(d-1)',
        'FAIL TO ID -GIVING FALSE/FICTITIOUS INFO PC 38.02(c)(2)',
        'EVADING ARREST DETENTION',
        'EVADING ARREST DETENTION W/PREV CONVICTION',
        'EVADING ARREST DETENTION W/VEH OR WATERCRAFT',
        'EVADING ARREST DETENTION W/PREV CONVICTION PC38.04(b1)',
    ],
    
    # Death investigations
    OffenseCategory.DEATH: [
        'ACCIDENTAL DEATH (NO OFFENSE)',
        'NATURAL DEATH (NO OFFENSE)',
        'UNEXPLAINED DEATH (NO OFFENSE)',
        'MURDER',
    ],
    
    # Animal-related
    OffenseCategory.ANIMAL: [
        'DOG BITE - INJURED PERSON',
        'ATTACK BY DANGEROUS DOG',
        'CRUELTY TO NON-LIVESTOCK ANMLS FAIL PROV/ABDN/TRNSPT/BI/OVWK',
        'CRUELTY TO NON-LIVESTOCK ANIMAL-TORTURE',
        'CRUELTY TO NON-LIVESTOCK ANIMALS: FAILURE TO PROVIDE FOR',
        'CRUELTY TO LIVESTOCK ANIMALS - PRELIMINARY INVESTIGATION',
        'CRUELTY NON-LIVESTOCK ANIMALS - PRELIMINARY INVESTIGATION',
        'CRUELTY TO NON-LIVESTOCK ANIMALS FAILURE TO PROVIDE FOR',
    ],
}


def categorize_offense(offense: str) -> Optional[OffenseCategory]:
    """
    Categorize an offense string into a high-level category.
    
    Args:
        offense: Offense description (e.g., 'ASSAULT -BODILY INJURY ONLY')
    
    Returns:
        OffenseCategory enum value or None
    """
    if not offense:
        return None
    
    offense_upper = offense.upper()
    
    # Check exact matches first
    for category, offenses in OFFENSE_TYPE_MAP.items():
        if offense in offenses:
            return category
    
    # Fall back to keyword matching
    for category, keywords in OFFENSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.upper() in offense_upper:
                return category
    
    return OffenseCategory.OTHER


def search_offenses_by_category(
    category: OffenseCategory,
    all_offenses: Optional[List[str]] = None
) -> List[str]:
    """
    Search for all offense types matching a category.
    
    Args:
        category: OffenseCategory to search for
        all_offenses: Optional list of offense strings to search within
    
    Returns:
        List of matching offense strings
    """
    if all_offenses is None:
        # Return predefined mappings
        return OFFENSE_TYPE_MAP.get(category, [])
    
    # Search within provided list
    matches = []
    for offense in all_offenses:
        if categorize_offense(offense) == category:
            matches.append(offense)
    
    return matches


def search_offenses_by_keyword(
    keyword: str,
    all_offenses: Optional[List[str]] = None,
    case_sensitive: bool = False
) -> List[str]:
    """
    Search for offenses containing a keyword.
    
    Args:
        keyword: Keyword to search for (e.g., 'gun', 'sex', 'drug')
        all_offenses: Optional list of offense strings to search within
        case_sensitive: Whether to perform case-sensitive search
    
    Returns:
        List of matching offense strings
    """
    if all_offenses is None:
        # Search through all predefined offenses
        all_offenses = []
        for offenses in OFFENSE_TYPE_MAP.values():
            all_offenses.extend(offenses)
    
    if not case_sensitive:
        keyword = keyword.lower()
        return [o for o in all_offenses if keyword in o.lower()]
    else:
        return [o for o in all_offenses if keyword in o]


def get_offense_categories() -> List[OffenseCategory]:
    """Get all available offense categories."""
    return list(OffenseCategory)


def get_category_keywords(category: OffenseCategory) -> Set[str]:
    """Get search keywords for a category."""
    return OFFENSE_KEYWORDS.get(category, set())
