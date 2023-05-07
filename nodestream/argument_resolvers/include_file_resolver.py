from typing import Type

from yaml import SafeLoader

from .arugment_resolver import ArgumentResolver


class IncludeFileResolver(ArgumentResolver):
    @classmethod
    def install_yaml_tag(cls, loader: Type[SafeLoader]):
        loader.add_constructor(
            "!include",
            lambda loader, node: cls.include_file(loader.construct_scalar(node)),
        )

    @staticmethod
    def resolve_argument(file_path: str):
        from ..pipeline.pipeline_file_loader import PipelineFileSafeLoader

        return PipelineFileSafeLoader.load_file_by_path(file_path)