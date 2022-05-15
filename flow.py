from dataclasses import dataclass
from datetime import timedelta
from logging import Logger
import prefect
from prefect import Flow, task

from db import (
    DBCreds,
    load_csv_to_stg_products,
    update_names_table,
    update_skus_table,
    update_products_table,
)


# tasks
@task(retry_delay=timedelta(minutes=3), max_retries=3)
def load_csv_to_stg_products_taskfn(
    *,
    db_creds: DBCreds,
    csv_path: str,
    chunksize: int = 1e5,
    verbose: bool = False,
):
    logger: Logger = prefect.context.get("logger")
    load_csv_to_stg_products(
        db_creds=db_creds,
        csv_path=csv_path,
        chunksize=chunksize,
        log_progress=logger.info if verbose else None,
    )


@task(retry_delay=timedelta(minutes=3), max_retries=3)
def update_skus_table_taskfn(db_creds: DBCreds):
    update_skus_table(db_creds)


@task(retry_delay=timedelta(minutes=3), max_retries=3)
def update_names_table_taskfn(db_creds: DBCreds):
    update_names_table(db_creds)


@task(retry_delay=timedelta(minutes=3), max_retries=3)
def update_products_table_taskfn(db_creds: DBCreds):
    update_products_table(db_creds)


##


@dataclass(frozen=True)
class FlowParameters:
    db_creds: DBCreds

    products_csv_path: str
    products_csv_chunksize: int = 1e5

    verbose: bool = False


def create_flow(*, flow_params: FlowParameters, flow_name: str) -> Flow:
    with Flow(flow_name) as flow:
        load_csv_to_stg_products_task = load_csv_to_stg_products_taskfn(
            db_creds=flow_params.db_creds,
            csv_path=flow_params.products_csv_path,
            chunksize=flow_params.products_csv_chunksize,
            verbose=flow_params.verbose,
        )

        update_skus_table_task = update_skus_table_taskfn(flow_params.db_creds)
        load_csv_to_stg_products_task.set_downstream(update_skus_table_task)

        update_names_table_task = update_names_table_taskfn(flow_params.db_creds)
        load_csv_to_stg_products_task.set_downstream(update_names_table_task)

        update_products_table_task = update_products_table_taskfn(flow_params.db_creds)
        load_csv_to_stg_products_task.set_downstream(update_products_table_task)
        update_skus_table_task.set_downstream(update_products_table_task)
        update_names_table_task.set_downstream(update_products_table_task)

    return flow
