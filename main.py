import logging
import sys
from datetime import datetime, timedelta

from automation_server_client import AutomationServer, Workqueue, WorkItemError, Credential, WorkItemStatus
from eflyt_client import EflytClient
from odk_tools.tracking import Tracker

procesnavn = "Flytteprocesser"
eflyt_client: EflytClient = None
tracker: Tracker = None


def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Hello from populate workqueue!")

    flyttedato_fra = (datetime.now() - timedelta(days=2)).strftime("%d-%m-%Y")
    flyttedato_til = (datetime.now() + timedelta(days=4)).strftime("%d-%m-%Y")
    flyttesager = eflyt_client.fremsøg_liste(flyttedato_fra=flyttedato_fra, flyttedato_til=flyttedato_til)

    print("hej")


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
