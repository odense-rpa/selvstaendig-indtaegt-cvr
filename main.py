import argparse
import asyncio
import logging
import os

from automation_server_client import (
    AutomationServer,
    Workqueue,
    WorkItemError,
    Credential,
    WorkItemStatus,
)
from odk_tools.tracking import Tracker
from odk_tools.reporting import report
from process.config import get_excel_mapping, load_excel_mapping
from virk_client import VirkClient


tracker: Tracker
virk_client: VirkClient

proces_navn = "Selvstændig indtægt CVR"


async def populate_queue(workqueue: Workqueue):
    borgere = get_excel_mapping()

    for cpr in borgere["Cpr"]:
        eksisterende_kødata = workqueue.get_item_by_reference(cpr, WorkItemStatus.NEW)

        if len(eksisterende_kødata) > 0:
            continue

        workqueue.add_item({"Cpr": cpr}, cpr)


async def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    for item in workqueue:
        with item:
            data = item.data  # Item data deserialized from json as dict

            try:
                oplysninger = virk_client.hent_deltager(data["Cpr"])

                if not oplysninger:
                    report(
                        report_id="selvstaendig_indtaegt_cvr",
                        group="Intet CVRnr",
                        json={
                            "Cpr": data["Cpr"],
                            "Resultat": "Intet CVRnr. fundet på borgeren",
                        },
                    )
                else:
                    oplysninger_data = (
                        oplysninger[0]
                        if isinstance(oplysninger, list) and len(oplysninger) > 0
                        else oplysninger
                    )

                    aktive_virksomheder = [
                        relation
                        for relation in oplysninger_data.get("virksomhedSummariskRelation", [])
                        if relation.get("virksomhed", {}).get("enhedstype") == "VIRKSOMHED"
                        and any(
                            livsforloeb.get("periode", {}).get("gyldigTil") is None
                            for livsforloeb in relation.get("virksomhed", {}).get("livsforloeb", [])
                        )
                    ]

                    for aktiv_virksomhed in aktive_virksomheder:
                        report(
                            report_id="selvstaendig_indtaegt_cvr",
                            group="Borgere med CVRnr",
                            json={
                                "Cpr": data["Cpr"],
                                "Resultat": f"CVRnr fundet: {aktiv_virksomhed["virksomhed"]["cvrNummer"]}. Antal: {len(aktive_virksomheder)}",
                            },
                        )

                tracker.track_task(process_name=proces_navn)

            except WorkItemError as e:
                # A WorkItemError represents a soft error that indicates the item should be passed to manual processing or a business logic fault
                logger.error(f"Error processing item: {data}. Error: {e}")
                item.fail(str(e))


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))

    ats = AutomationServer.from_environment()
    workqueue = ats.workqueue()

    certifikat_sti = os.getenv("CERTIFIKATER", "/certifikater")
    
    virk_client = VirkClient(
        certifikat_sti=os.path.join(certifikat_sti, "virk.crt"),
        certifikat_nøglefil=os.path.join(certifikat_sti, "virk.key"),
    )

    tracking_credential = Credential.get_credential("Odense SQL Server")

    tracker = Tracker(
        username=tracking_credential.username, password=tracking_credential.password
    )

    parser = argparse.ArgumentParser(description=proces_navn)
    parser.add_argument(
        "--citizens",
        help="Path to the file containing the list of citizens to process (one CPR per line)",
        default=os.path.join(project_root, "documents", "Borgere.xlsx"),
    )
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Populate the queue with test data and exit",
    )
    args = parser.parse_args()

    if not os.path.isabs(args.citizens):
        args.citizens = os.path.join(project_root, args.citizens)

    # Validate Excel file exists
    if not os.path.isfile(args.citizens):
        raise FileNotFoundError(f"Excel file not found: {args.citizens}")

    # Load excel mapping data once on startup
    load_excel_mapping(args.citizens)

    # Queue management
    if args.queue:
        workqueue.clear_workqueue(WorkItemStatus.NEW)
        asyncio.run(populate_queue(workqueue))
        exit(0)

    # Process workqueue
    asyncio.run(process_workqueue(workqueue))
