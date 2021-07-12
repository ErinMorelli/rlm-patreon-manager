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

__all__ = ['videos', 'login_user']


def login_user(content, with_account=False):
    """Decorator to automatically log user in for CLI actions."""
    def inner(func):
        def wrapper(*args, **kwargs):
            account = content.login_user()
            if not account:
                return
            if with_account:
                kwargs['account'] = account
            func(*args, **kwargs)
        return wrapper
    return inner
