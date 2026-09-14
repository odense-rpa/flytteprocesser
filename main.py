import logging
import sys
from datetime import datetime, timedelta

from automation_server_client import AutomationServer, Workqueue, WorkItemError, Credential, WorkItemStatus
from eflyt_client import EflytClient
from odk_tools.tracking import Tracker

procesnavn = "Flytteprocesser"
eflyt_client: EflytClient = None
tracker: Tracker = None

# Svarer til "Flytteprocesser"-kollektionen i Blue Prism-processen: de kombinationer
# af sagstilstand/flyttetype/indeholder status der skal fremsøges og lægges i køen.
FLYTTEPROCESSER = [
    {"sagstilstand": "Ubehandlet", "flyttetype": "Simpel flytning", "indeholder_status": "Ubehandlet"},
    {"sagstilstand": "Ubehandlet", "flyttetype": "Særlig adresse", "indeholder_status": "Ubehandlet"},
    {"sagstilstand": "Ubehandlet", "flyttetype": "Boligselskab", "indeholder_status": "Ubehandlet"},
]

# Svarer til "Korrekt flyttetype?"-beslutningen i Blue Prism-processen.
ACCEPTEREDE_FLYTTETYPER = {
    "Simpel flytning",
    "Boligselskab, Særlig adresse",
    "Særlig adresse, Boligselskab",
    "Boligselskab",
}


def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Hello from populate workqueue!")

    # Svarer til "Sæt datoer" i Blue Prism-processen.
    flyttedato_fra = (datetime.now() - timedelta(days=4)).strftime("%d-%m-%Y")
    flyttedato_til = (datetime.now() + timedelta(days=2)).strftime("%d-%m-%Y")

    for proces in FLYTTEPROCESSER:
        flyttesager = eflyt_client.fremsøg_liste(
            flyttedato_fra=flyttedato_fra,
            flyttedato_til=flyttedato_til,
            sagstilstand=proces["sagstilstand"],
            flyttetype=proces["flyttetype"],
            indeholder_status=proces["indeholder_status"],
        )

        for sag in flyttesager:
            # Svarer til "Korrekt flyttetype?"
            if sag["flyttetype"] not in ACCEPTEREDE_FLYTTETYPER:
                continue

            sagsnummer = sag["sagsnummer"]

            # Svarer til "Fundet i kø": spring over hvis sagen allerede findes i
            # køen og ikke er fejlet (fejlede sager må gerne fremsøges igen).
            eksisterende_items = workqueue.get_item_by_reference(sagsnummer)
            if any(item.status != WorkItemStatus.FAILED for item in eksisterende_items):
                continue

            # Svarer til "Sæt SR data" + "Tilføj til kø".
            item_data = {
                "flyttedato": sag["flyttedato"],
                "sagsnummer": sagsnummer,
                "flyttetype": sag["flyttetype"],
                "status": sag["status"],
                "cpr": sag["cpr"],
                "navn": sag["navn"],
                "sagsbehandler": sag["sagsbehandler"],
            }
            workqueue.add_item(data=item_data, reference=sagsnummer)




def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Hello from process workqueue!")

    for item in workqueue:
        with item:
            data = item.data  # Item data deserialized from json as dict
 
            try:
                # Process the item here
                pass
            except WorkItemError as e:
                # A WorkItemError represents a soft error that indicates the item should be passed to manual processing or a business logic fault
                logger.error(f"Error processing item: {data}. Error: {e}")
                item.fail(str(e))


if __name__ == "__main__":
    ats = AutomationServer.from_environment()
    workqueue = ats.workqueue()

    # Initialize external systems for automation here..
    eflyt_credentials = Credential.get_credential("eFlyt")
    tracking_credential = Credential.get_credential("Odense SQL Server")
    eflyt_client = EflytClient(
        base_url=eflyt_credentials.data["url"],
        username=eflyt_credentials.username,
        password=eflyt_credentials.password
    )

    tracker = Tracker(
        username=tracking_credential.username, password=tracking_credential.password
    )
    # Queue management
    if "--queue" in sys.argv:
        workqueue.clear_workqueue(WorkItemStatus.NEW)
        populate_queue(workqueue)
        exit(0)

    # Process workqueue
    process_workqueue(workqueue)
