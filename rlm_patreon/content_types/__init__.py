"""
Copyright (C) 2021 Erin Morelli.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see [https://www.gnu.org/licenses/].
"""

from pathlib import Path
from inspect import isclass
from pkgutil import iter_modules
from importlib import import_module

from rlm_patreon.content import PatreonContent


__all__ = ['get_content_types']


def get_content_types():
    """Dynamically build a list of all content types in the module."""
    types = []
    package_dir = Path(__file__).resolve().parent

    # Iterate over the modules within the package
    for (_, module_name, _) in iter_modules([package_dir]):
        module = import_module(f"{__name__}.{module_name}")

        # Get each module attribute
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)

            # Check for child classes of the base content class
            if isclass(attribute) and issubclass(attribute, PatreonContent):
                types.append(attribute)

    # Return the list of type classes
    return types
