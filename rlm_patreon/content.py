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

import os

import click
from requests import Session, RequestException, cookies

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from sqlalchemy_utils import EmailType
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy import Table, Column, String, DateTime, func
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from rlm_patreon.content_types import login_user


class PatreonContent:
    """Base content class that also provides account access."""
    command = 'account'
    model_name = command
    # URLs for making requests
    cookie_domain = 'patreon.com'
    base_url = f'https://www.{cookie_domain}'
    rlm_url = f'{base_url}/redlettermedia'
    user_url = f'{base_url}/api/current_user'
    login_endpoint = '/api/login'
    # Common headers for HTTP requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) '
                      'Gecko/20100101 Firefox/89.0'
    }
    # Set CLI details for account management
    command_help = 'Manage your Patreon account.'
    commands = ['login', 'update', 'show']

    def __init__(self, manager):
        """Setup details for content class."""
        self.manager = manager
        self.db = self.manager.get_session()
        self.model = self.manager.models.get(self.model_name)

    def session(self, session_id):
        """Create a new API session with the correct cookies and headers."""
        session = Session()
        # Create a new cookie jar with the user's session ID
        jar = cookies.RequestsCookieJar()
        jar.set('session_id', session_id, domain='patreon.com', path='/')
        # Add cookies and headers to session
        session.cookies = jar
        session.headers = self.headers
        # Return new session object
        return session

    def _get_account(self):
        """Locate an account in the database."""
        model = self.manager.models.get('account')
        try:
            account = self.db.query(model).one()
        except NoResultFound:
            # Ask user to login
            self.manager.warning('Please login to your account first.')
            return None
        except MultipleResultsFound:
            # List all available accounts
            click.echo('Multiple accounts found:')
            all_accounts = self.db.query(model).all()
            for idx, acct in enumerate(all_accounts):
                click.echo(f' [{idx}] {acct.email}')
            # Prompt user to select an account
            user_idx = click.prompt(
                '\nEnter account number',
                type=click.Choice(range(len(all_accounts))),
                show_choices=False,
                default='0'
            )
            # Use the selected account
            account = all_accounts[int(user_idx)]
        # Returns the account or none
        return account

    def _check_session(self, account):
        """Check if the user's session ID is still valid."""
        res = self.session(account.session_id).get(self.user_url)

        try:
            # Check the results
            res.raise_for_status()
            email = res.json()['data']['attributes']['email']
        except RequestException as ex:
            # Handle bad requests
            self.manager.error(f'Unable to login: {str(ex)}')
            return False
        except ValueError:
            # Handle malformed API response
            self.manager.error('Unable to login: API error, try again later')
            return False

        # Handle bad session
        if email != account.email:
            self.manager.error('Unable to login: expired session')
            return False

        # Return session is valid
        return True

    def login_user(self):
        """Login with Patreon credentials."""
        account = self._get_account()
        if not account:
            return None

        # If the session ID is valid, skip login request
        if self._check_session(account):
            return account

        # Make the login request
        success = self._make_login_request(
            account.email,
            self.manager.decode(account.password)
        )
        if not success:
            return None

        # Return the logged in account
        return account

    @property
    def _login_js(self):
        """The JS code to execute during API login request."""
        return """return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            var data = {
                data: {
                    type: "user",
                    attributes: {
                        email: "%s",
                        password: "%s"
                    },
                    relationships: {}
                }
            };
            xhr.open("POST", "%s");
            xhr.withCredentials = true;
            xhr.setRequestHeader("X-CSRF-Signature", window.patreon.csrfSignature);
            xhr.setRequestHeader("Content-Type", "application/vnd.api+json");
            xhr.onreadystatechange = () => {
                if (this.readyState == this.HEADERS_RECEIVED) {
                    resolve(xhr.getAllResponseHeaders());
                }
            }
            xhr.send(JSON.stringify(data));
        });"""

    def _make_login_request(self, email, password):
        """Make a login request with the given credentials"""
        options = webdriver.chrome.options.Options()
        options.add_argument('headless')

        # Load page in headless Chrome
        driver = webdriver.Chrome(options=options)
        driver.get(self.rlm_url)

        # Wait for login JS to execute on the page
        script = self._login_js % (email, password, self.login_endpoint)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script(script))

        # Get the session ID from the browser cookies
        for cookie in driver.get_cookies():
            if cookie['name'] == 'session_id':
                return cookie['value']

        # Handle login errors, usually due to device verification
        self.manager.error('Unable to login: device needs email verification')
        return None

    def _get_download_dir(self, dest, account, with_model=True):
        """Get and validate download directory."""
        dest_dir = dest if dest else account.download_dir
        # Append the model name
        if with_model:
            dest_dir = os.path.join(dest_dir, self.model_name.capitalize())
        # Check that download path exists
        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)
        return dest_dir

    def _get_download_path(self, base_path, file_name, yes):
        """Get and validate download file path."""
        file_path = os.path.join(base_path, file_name)

        # Check if file already exists
        if os.path.isfile(file_path):
            self.manager.warning(f'File "{file_path}" already exists')
            return None

        # Confirm the download
        if not yes:
            if not click.confirm(f'Download file to {file_path}?'):
                return None
        else:
            click.echo(f'Downloading file to {file_path}')
        return file_path

    @staticmethod
    def table(metadata):
        """Account database table definition."""
        return Table(
            'account',
            metadata,
            Column('email', EmailType, primary_key=True, unique=True),
            Column('password', BLOB, nullable=False),
            Column('download_dir', String, nullable=True),
            Column('session_id', String, nullable=True),
            Column('last_updated', DateTime, server_default=func.now(),
                   onupdate=func.now(), nullable=False)
        )

    @property
    def login(self):
        """Command to login user."""
        @click.command(help='Login with your Patreon credentials.')
        @click.option('-e', '--email', prompt='Email')
        @click.password_option('-p', '--password')
        def fn(email, password):
            """Login with your Patreon credentials."""
            account = self.db.query(self.model) \
                .filter_by(email=email) \
                .first()
            # Add account if it is not found
            if not account:
                # Attempt to login
                session_id = self._make_login_request(email, password)
                # Save the account if successful
                if session_id:
                    account = self.model(
                        email=email,
                        password=self.manager.encode(password),
                        download_dir=self.manager.user_path,
                        session_id=session_id
                    )
                    self.db.add(account)
                    self.db.commit()
                    self.manager.success('Successfully logged in!')
                return
            # Attempt to login
            good = self._make_login_request(email, password)
            # If the account was found, confirm password change
            if good and click.confirm('Confirm password change for account'):
                account.password = self.manager.encode(password)
                self.db.commit()
                self.manager.success('Successfully updated password!')
        return fn

    @property
    def update(self):
        """Command to update account info."""
        @click.command(help='Update account information.')
        @click.option('--download_dir', type=click.Path(exists=True),
                      help='Set path where files will be downloaded.')
        @login_user(self, with_account=True)
        def fn(download_dir, account):
            """Update account information."""
            if not download_dir:
                click.echo(click.get_current_context().get_help())
                return
            # Update the download directory in the database
            account.download_dir = download_dir
            self.db.commit()
            self.manager.success(f'Download path set to: {download_dir}')
        return fn

    @property
    def show(self):
        """Command to show account info."""
        @click.command(help='Display account information.')
        @login_user(self, with_account=True)
        def fn(account):
            """Display account information."""
            form = u'{0:>15}: {1}'
            account_data = '\n'.join([
                form.format('Email', account.email),
                form.format('Password', '*********** [hidden for security]'),
                form.format('Download Path', account.download_dir)
            ])
            click.echo(account_data)
        return fn

    @property
    def cli(self):
        """Command grouping for content actions."""
        @click.group()
        def fn():
            """Base group function for creating the CLI."""
        # Set the description
        fn.help = self.command_help
        # Add all account commands
        for cmd in self.commands:
            fn.add_command(getattr(self, cmd), cmd)
        return fn
