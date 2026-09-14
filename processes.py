"""Handlere for de enkelte flyttetyper i "BKF - flytteprocesser".

Hver funktion svarer til et subsheet i Blue Prism-processen og modtager
sagsnummer, item-data samt en logget ind EflytClient-instans.
"""

from datetime import datetime

from eflyt_client import EflytClient


def _cpr_til_alder(cpr: str, i_dag: datetime | None = None) -> int:
    """Beregner en persons alder ud fra et dansk CPR-nummer.

    Svarer til "Utility - Odk: String: Cpr to birthday". CPR-formatet er
    DDMMYY-XXXX, hvor det 7. ciffer (første ciffer i løbenummeret) sammen med
    årstallet afgør århundredet, jf. de officielle CPR-regler.
    """
    cifre = cpr.replace("-", "").strip()
    dag = int(cifre[0:2])
    måned = int(cifre[2:4])
    år = int(cifre[4:6])
    syvende_ciffer = int(cifre[6])

    if syvende_ciffer in (0, 1, 2, 3):
        århundrede = 1900
    elif syvende_ciffer == 4:
        århundrede = 2000 if år <= 36 else 1900
    elif syvende_ciffer in (5, 6, 7, 8):
        århundrede = 2000 if år <= 57 else 1800
    else:  # 9
        århundrede = 2000 if år <= 36 else 1900

    fødselsdato = datetime(århundrede + år, måned, dag)
    i_dag = i_dag or datetime.now()

    alder = i_dag.year - fødselsdato.year
    if (i_dag.month, i_dag.day) < (fødselsdato.month, fødselsdato.day):
        alder -= 1

    return alder


def handle_simpel_flytning(
    eflyt_client: EflytClient, sagsnummer: str, data: dict
) -> None:
    """Svarer til subsheetet "BKF - flytteprocesser" for flyttetypen
    "Simpel flytning".

    Fremsøger sagen, tæller hvor mange beboere der har en registreret
    fraflytningsadresse, og godkender sagen automatisk hvis alle beboere har
    en fraflytningsadresse og deres antal stemmer overens. Ellers markeres
    sagen til manuel brevudsendelse ved at ændre flyttetypen.
    """
    # Svarer til "Hent sag".
    sagsdetaljer = eflyt_client.hent_sagsdetaljer(sagsnummer)
    beboere = sagsdetaljer["beboere"]

    antal_beboere = len(beboere)
    # Svarer til "Tæl fraflytninger" (Utility - Odk Linq: Count med filter
    # "[Fraflytning til] <> ''").
    antal_fraflytninger = sum(
        1 for beboer in beboere if beboer["fraflytning_til"] != ""
    )

    # Svarer til "Skal vi sende brev?": Ingen fraflytter, men der bor nogen -
    # eller uoverensstemmelse mellem antal beboere og antal fraflytninger.
    skal_sende_brev = (
        antal_fraflytninger == 0 and antal_beboere > 0
    ) or antal_beboere != antal_fraflytninger

    if skal_sende_brev:
        # Svarer til "Sæt 'simpel flyt - send brev'" + at "Simpel flyt - send
        # brev"-subsheetet kaldes lige efter i samme kørsel.
        data["flyttetype"] = "Simpel flytning - send brev"
        handle_simpel_flyt_send_brev(eflyt_client, sagsnummer, data)
    else:
        # Svarer til "Godkend sag".
        eflyt_client.godkend_sag(sagsnummer)


def handle_simpel_flyt_send_brev(
    eflyt_client: EflytClient, sagsnummer: str, data: dict
) -> None:
    """Svarer til subsheetet "Simpel flyt - send brev".

    Finder ud af hvem af de tilbageværende beboere (dem uden en registreret
    fraflytningsadresse) der har boet længst på adressen, og sender en
    logiværtserklæring til vedkommende - men kun hvis der er plads nok til
    både de nuværende beboere og de indflyttere sagen omhandler.
    """
    sagsdetaljer = eflyt_client.hent_sagsdetaljer(sagsnummer)
    beboere = sagsdetaljer["beboere"]
    antal_beboere = len(beboere)

    # Svarer til loopet "Loop Beboere": fjern beboere der selv fraflytter
    # adressen ("Fjern beboer"), og beregn alder for de resterende
    # ("Find alder på beboere").
    tilbageværende_beboere = []
    for beboer in beboere:
        if beboer["fraflytning_til"] != "":
            continue
        beboer["alder"] = _cpr_til_alder(beboer["cpr"])
        tilbageværende_beboere.append(beboer)

    # Svarer til "Tæl beboere over 18" (Utility - Odk Linq: Count med filter
    # "[Alder] >= 16" - navnet på tællevariablen matcher ikke selve filteret
    # i den oprindelige Blue Prism-proces, men vi bevarer adfærden).
    antal_beboere_over_18 = sum(
        1 for beboer in tilbageværende_beboere if beboer["alder"] >= 16
    )

    # Svarer til "Sorter beboere på tilflytningsdato" (ascending) + "Sæt
    # længstboende": den først tilflyttede har boet længst på adressen.
    tilbageværende_beboere.sort(
        key=lambda beboer: datetime.strptime(beboer["tilflytningsdato"], "%d-%m-%Y")
    )

    if not tilbageværende_beboere:
        # Ingen tilbageværende beboere at sende brev til.
        return

    dato_længstboende = tilbageværende_beboere[0]["tilflytningsdato"]

    # Svarer til "Find borgere med længste dato" + "Sorter beboere på alder"
    # (descending): blandt de(n) længstboende vælges den ældste.
    kandidater = [
        beboer
        for beboer in tilbageværende_beboere
        if beboer["tilflytningsdato"] == dato_længstboende
    ]
    kandidater.sort(key=lambda beboer: beboer["alder"], reverse=True)
    logivært = kandidater[0]

    # Svarer til "Flyttedata.Antal indflyttere".
    antal_rum = float(sagsdetaljer["antal_rum"])
    antal_indflyttere = sagsdetaljer["antal_indflyttere"]

    dags_dato = datetime.now().strftime("%d-%m-%Y")

    # Svarer til "Er der plads?".
    if antal_rum >= antal_beboere + antal_indflyttere:
        # Svarer til "Send brev: logivært beboere".
        # TODO: eflyt_client.send_brev skal implementeres - sender et brev af
        # en given type til en modtager og returnerer om modtageren er
        # digital (svarer til Blue Prism-handlingen "Send brev").
        digital_borger = eflyt_client.send_brev(
            sagsnummer=sagsnummer,
            brevtype="- Logiværtserklæring beboer",
            modtager=logivært["navn"],
            antal_beboere=antal_beboere_over_18,
        )

        if digital_borger:
            data["besked"] = f"{dags_dato}: Der er sendt logivært - Tyra"
        else:
            data["besked"] = f"{dags_dato}: Borger er ikke digital - Tyra"
    else:
        data["besked"] = f"{dags_dato}: Der er ikke plads - Tyra"


def handle_særlig_adresse_boligselskab(
    eflyt_client: EflytClient, sagsnummer: str, data: dict
) -> None:
    """Svarer til subsheetet for flyttetyperne "Særlig adresse, Boligselskab"
    og "Boligselskab, Særlig adresse".

    TODO: Endnu ikke implementeret - mangler resten af subsheetet.
    """
    raise NotImplementedError(
        "handle_saerlig_adresse_boligselskab er endnu ikke implementeret"
    )


def handle_boligselskab(
    eflyt_client: EflytClient, sagsnummer: str, data: dict
) -> None:
    """Svarer til subsheetet for flyttetypen "Boligselskab".

    TODO: Endnu ikke implementeret - mangler subsheetet.
    """
    raise NotImplementedError("handle_boligselskab er endnu ikke implementeret")
