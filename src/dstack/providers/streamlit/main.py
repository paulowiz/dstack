import argparse
from argparse import ArgumentParser
from typing import List, Optional

from dstack import App, JobSpec
# TODO: Provide job.applications (incl. application name, and query)
from dstack.providers import Provider


class StreamlitProvider(Provider):
    def __init__(self):
        super().__init__("streamlit")
        self.target = None
        self.before_run = None
        self.python = None
        self.version = None
        self.args = None
        self.requirements = None
        self.env = None
        self.artifacts = None
        self.working_dir = None
        self.resources = None
        self.image_name = None

    def load(self):
        super()._load(schema="schema.yaml")
        self.target = self.workflow.data["target"]
        self.before_run = self.workflow.data.get("before_run")
        # TODO: Handle numbers such as 3.1 (e.g. require to use strings)
        self.python = self._save_python_version("python")
        self.version = self.workflow.data.get("version")
        self.args = self.workflow.data.get("args")
        self.requirements = self.workflow.data.get("requirements")
        self.env = self.workflow.data.get("environment") or {}
        self.artifacts = self.workflow.data.get("artifacts")
        self.working_dir = self.workflow.data.get("working_dir")
        self.resources = self._resources()
        self.image_name = self._image_name()

    def _create_parser(self, workflow_name: Optional[str]) -> Optional[ArgumentParser]:
        parser = ArgumentParser(prog="dstack run " + (workflow_name or self.provider_name))
        self._add_base_args(parser)
        if not workflow_name:
            parser.add_argument("target", metavar="TARGET", type=str)
            parser.add_argument("args", metavar="ARGS", nargs=argparse.ZERO_OR_MORE)
        return parser

    def parse_args(self):
        parser = self._create_parser(self.workflow_name)
        args, unknown = parser.parse_known_args(self.provider_args)
        self._parse_base_args(args)
        if self.run_as_provider:
            self.workflow.data["target"] = args.target
            _args = args.args + unknown
            if _args:
                self.workflow.data["args"] = _args

    def create_job_specs(self) -> List[JobSpec]:
        return [JobSpec(
            image_name=self.image_name,
            commands=self._commands(),
            env=self.env,
            working_dir=self.working_dir,
            artifacts=self.artifacts,
            port_count=2,
            requirements=self.resources,
            apps=[App(
                port_index=1,
                app_name="streamlit",
            )]
        )]

    def _image_name(self) -> str:
        cuda_is_required = self.resources and self.resources.gpus
        return f"dstackai/python:{self.python}-cuda-11.1" if cuda_is_required else f"python:{self.python}"

    def _commands(self):
        commands = [
            "pip install streamlit" + (f"=={self.version}" if self.version else ""),
        ]
        if self.before_run:
            commands.extend(self.before_run)
        args_init = ""
        if self.args:
            if isinstance(self.args, str):
                args_init += " " + self.args
            if isinstance(self.args, list):
                args_init += " " + ",".join(map(lambda arg: "\"" + arg.replace('"', '\\"') + "\"", self.args))
        commands.append(
            f"streamlit run --server.port $PORT_1 --server.enableCORS=true --browser.serverAddress 0.0.0.0 "
            f"--server.headless true {self.target}{args_init} "
        )
        return commands


def __provider__():
    return StreamlitProvider()


if __name__ == '__main__':
    __provider__().submit_jobs()
