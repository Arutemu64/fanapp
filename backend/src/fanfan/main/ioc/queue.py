from dishka import Provider, Scope, provide
from procrastinate import App

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.procrastinate.job_queue import ProcrastinateJobQueue
from fanfan.presentation.worker.app import app, routes
from fanfan.presentation.worker.config import WorkerConfig


class QueueProvider(Provider):
    scope = Scope.APP

    @provide
    def get_worker_config(self, config: EnvConfig) -> WorkerConfig:
        return config.worker

    @provide
    def get_app(self) -> App:
        return app

    @provide
    def get_job_queue(self, procrastinate_app: App) -> ProcrastinateJobQueue:
        return ProcrastinateJobQueue(procrastinate_app, routes)
