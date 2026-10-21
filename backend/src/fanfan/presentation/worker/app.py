from procrastinate import App, PsycopgConnector

from fanfan.adapters.procrastinate.job_queue import MessageRoutes
from fanfan.presentation.worker.routes.maintenance import maintenance_tasks
from fanfan.presentation.worker.routes.notifications import notifications_tasks
from fanfan.presentation.worker.routes.schedule import schedule_tasks
from fanfan.presentation.worker.routes.sync import sync_tasks
from fanfan.presentation.worker.subscriber import message_routes

# The process's one App, built at import because adding a blueprint renames its
# tasks in place and may only happen once. The connector carries no settings:
# the worker opens it with its own pool (main/worker.py), and the api never
# opens it at all — it only writes jobs on the request's own connection
# (adapters/procrastinate/job_queue.py).
app = App(connector=PsycopgConnector())
app.add_tasks_from(maintenance_tasks, namespace="maintenance")
app.add_tasks_from(notifications_tasks, namespace="notifications")
app.add_tasks_from(schedule_tasks, namespace="schedule")
app.add_tasks_from(sync_tasks, namespace="sync")

# Read after the blueprints are added, so each task carries its final name.
routes: MessageRoutes = message_routes()
