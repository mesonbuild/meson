import abc
import re
from typing import Dict, Union

class SampleImpl(metaclass=abc.ABCMeta):
    """
    Base class for Sample implementation.
    """

    def __init__(self, args):
        """
        Initialize SampleImpl instance.
        
        Args:
            args: Arguments object.
        """
        self.name = args.name
        self.version = args.version
        self.lowercase_token = re.sub(r'[^a-z0-9]', '_', self.name.lower())
        self.uppercase_token = self.lowercase_token.upper()
        self.capitalized_token = self.lowercase_token.capitalize()

    @abc.abstractmethod
    def create_executable(self):
        """
        Abstract method to create executable.
        """
        pass

    @abc.abstractmethod
    def create_library(self):
        """
        Abstract method to create library.
        """
        pass

    @property
    @abc.abstractmethod
    def exe_template(self):
        """
        Abstract property for executable template.
        """
        pass

    @property
    @abc.abstractmethod
    def exe_meson_template(self):
        """
        Abstract property for executable Meson template.
        """
        pass

    @property
    @abc.abstractmethod
    def lib_template(self):
        """
        Abstract property for library template.
        """
        pass

    @property
    @abc.abstractmethod
    def lib_test_template(self):
        """
        Abstract property for library test template.
        """
        pass

    @property
    @abc.abstractmethod
    def lib_meson_template(self):
        """
        Abstract property for library Meson template.
        """
        pass

    @property
    @abc.abstractmethod
    def source_ext(self):
        """
        Abstract property for source file extension.
        """
        pass


class ClassImpl(SampleImpl):
    """
    Implementation for class-based languages like Java and C#.
    """

    def create_executable(self):
        """
        Create executable.
        """
        source_name = f'{self.capitalized_token}.{self.source_ext}'
        with open(source_name, 'w', encoding='utf-8') as f:
            f.write(self.exe_template.format(project_name=self.name,
                                             class_name=self.capitalized_token))
        with open('meson.build', 'w', encoding='utf-8') as f:
            f.write(self.exe_meson_template.format(project_name=self.name,
                                                   exe_name=self.name,
                                                   source_name=source_name,
                                                   version=self.version))

    def create_library(self):
        """
        Create library.
        """
        lib_name = f'{self.capitalized_token}.{self.source_ext}'
        test_name = f'{self.capitalized_token}_test.{self.source_ext}'
        kwargs = self._lib_kwargs()
        with open(lib_name, 'w', encoding='utf-8') as f:
            f.write(self.lib_template.format(**kwargs))
        with open(test_name, 'w', encoding='utf-8') as f:
            f.write(self.lib_test_template.format(**kwargs))
        with open('meson.build', 'w', encoding='utf-8') as f:
            f.write(self.lib_meson_template.format(**kwargs))

    def _lib_kwargs(self):
        """
        Get language-specific keyword arguments.
        
        Returns:
            Dict[str, Union[str, int]]: Dictionary of key-value pairs.
        """
        return {
            'utoken': self.uppercase_token,
            'ltoken': self.lowercase_token,
            'class_test': f'{self.capitalized_token}_test',
            'class_name': self.capitalized_token,
            'source_file': f'{self.capitalized_token}.{self.source_ext}',
            'test_source_file': f'{self.capitalized_token}_test.{self.source_ext}',
            'test_exe_name': f'{self.lowercase_token}_test',
            'project_name': self.name,
            'lib_name': self.lowercase_token,
            'test_name': self.lowercase_token,
            'version': self.version,
        }


class FileImpl(SampleImpl):
    """
    Implementation for file-based languages without headers.
    """

    def create_executable(self):
        """
        Create executable.
        """
        source_name = f'{self.lowercase_token}.{self.source_ext}'
        with open(source_name, 'w', encoding='utf-8') as f:
            f.write(self.exe_template.format(project_name=self.name))
        with open('meson.build', 'w', encoding='utf-8') as f:
            f.write(self.exe_meson_template.format(project_name=self.name,
                                                   exe_name=self.name,
                                                   source_name=source_name,
                                                   version=self.version))

    def create_library(self):
        """
        Create library.
        """
        lib_name = f'{self.lowercase_token}.{self.source_ext}'
        test_name = f'{self.lowercase_token}_test.{self.source_ext}'
        kwargs = self._lib_kwargs()
        with open(lib_name, 'w', encoding='utf-8') as f:
            f.write(self.lib_template.format(**kwargs))
        with open(test_name, 'w', encoding='utf-8') as f:
            f.write(self.lib_test_template.format(**kwargs))
        with open('meson.build', 'w', encoding='utf-8') as f:
            f.write(self.lib_meson_template.format(**kwargs))

    def _lib_kwargs(self):
        """
        Get language-specific keyword arguments.
        
        Returns:
            Dict[str, Union[str, int]]: Dictionary of key-value pairs.
        """
        kwargs = super()._lib_kwargs()
        kwargs['header_file'] = f'{self.lowercase_token}.{self.header_ext}'
        return kwargs


class FileHeaderImpl(FileImpl):
    """
    Implementation for file-based languages with headers.
    """

    @property
    @abc.abstractmethod
    def header_ext(self):
        """
        Abstract property for header file extension.
        """
        pass

    @property
    @abc.abstractmethod
    def lib_header_template(self):
        """
        Abstract property for library header template.
        """
        pass

    def create_library(self):
        """
        Create library.
        """
        super().create_library()
        kwargs = self._lib_kwargs()
        with open(kwargs['header_file'], 'w', encoding='utf-8') as f:
            f.write(self.lib_header_template.format_map(kwargs))
