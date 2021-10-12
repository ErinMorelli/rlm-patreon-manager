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

from urllib.parse import urlparse
from textwrap import shorten, TextWrapper

import click
from tqdm import tqdm
from pyquery import PyQuery
from dateutil import parser
from tabulate import tabulate, tabulate_formats
from vimeo_downloader import Vimeo, RequestError

from sqlalchemy_utils.types import URLType
from sqlalchemy import Table, Column, Date, DateTime, Integer, String, func

from rlm_patreon.content import PatreonContent

from pprint import pprint


class VideoContent(PatreonContent):
    """Manage Patreon video content."""
    command = 'videos'
    model_name = command
    # Video-specific URLs for HTTP requests
    posts_url = f'{PatreonContent.base_url}/api/posts'
    # Set CLI details for videos
    command_help = 'Manage Patreon exclusive videos.'
    commands = ['list', 'update', 'show', 'download', 'open']

    def _update_videos(self, session_id, limit=25):
        """Add new video content to database."""
        session = self.session(session_id)

        #  Set up progress bar data
        progress_bar = {
            'total': limit,
            'unit': 'videos',
            'desc': 'Scanning for new videos',
            'bar_format': '{l_bar}{bar}| {n_fmt}/{total_fmt} {unit}'
        }

        # Get all video posts
        with tqdm(**progress_bar) as pbar:
            all_posts = self._get_video_posts(
                session, pbar, limit, [], self.posts_url)

        # Add videos to the database
        added = []
        for post in all_posts:
            video = self._create_video(post)
            if video:
                added.append(video)
                self.db.add(video)

        # Only commit the changes if anything was added
        if added:
            self.db.commit()

        # Return the list of added videos
        return added

    def _get_video_posts(self, session, pbar, count, posts, posts_url):
        """Recursively retrieves video posts from the API."""
        res = session.get(posts_url, params={
            'include': 'campaign',
            'fields[campaign]': 'name,url',
            'fields[post]': 'content,current_user_can_view,embed,image,'
                            'is_paid,meta_image_url,post_file,'
                            'post_metadata,published_at,patreon_url,'
                            'post_type,thumbnail_url,title,url,'
                            'was_posted_by_campaign_owner',
            'filter[campaign_id]': '90486',
            'filter[contains_exclusive_posts]': 'true',
            'filter[is_draft]': 'false',
            'sort': '-published_at'
        })
        res_json = res.json()

        # Parse posts results
        for post in res_json['data']:
            if (
                    post['type'] == 'post' and
                    post['attributes']['post_type'] == 'video_embed' and
                    post['attributes']['embed']['provider'] == 'Vimeo'
            ):
                posts.append(post['attributes'])
                pbar.update(1)

                # Check if we have reached the limit
                if len(posts) == count:
                    return posts

        # Get next URL
        next_url = res_json['links']['next']

        # Recurse to get more posts
        return self._get_video_posts(session, pbar, count, posts, next_url)

    def _find_video(self, title, url):
        """Searches for a video in the database by title and URL."""
        return self.db.query(self.model)\
            .filter_by(title=title, url=url)\
            .one_or_none()

    def _create_video(self, post):
        """Creates a new video entry in the database."""
        video_title = post['title']
        video_url = post['url']

        # Exit if the video already exists
        if self._find_video(video_title, video_url):
            return None

        # Parse vimeo URL
        parsed_url = urlparse(post['embed']['url'])
        vimeo_url = os.path.dirname(parsed_url.geturl()) \
            if os.path.dirname(parsed_url.path) != '/' else parsed_url.geturl()

        # Get video date
        video_date = parser.parse(post['published_at']).date()

        # Get the video description
        video_desc = post['content']
        if video_desc != '':
            html = PyQuery(video_desc)
            video_desc = '\n\n'.join([p.text or '' for p in html('p')])

        # Return the new video object
        return self.model(
            title=video_title,
            description=video_desc,
            date=video_date,
            url=video_url,
            video=vimeo_url
        )

    def _download_video(self, video, video_path, yes):
        """Downloads a video file to the specified path."""
        vimeo = Vimeo(video.video, embedded_on=video.url)

        # Select the best quality stream
        stream = vimeo.best_stream

        # Format the file name from the title
        file_name = stream.title
        if not file_name.endswith(".mp4"):
            file_name += ".mp4"

        # Check to see if the video already exists
        file_path = self._get_download_path(video_path, file_name, yes)
        if not file_path:
            return

        # Perform the download
        stream.download(download_directory=video_path)

        # Check that the file was downloaded
        if not os.path.isfile(file_path):
            self.manager.error(f'Problem downloading file: {file_path}')

    @staticmethod
    def table(metadata):
        """Video database table definition."""
        return Table(
            'videos',
            metadata,
            Column('video_id', Integer, primary_key=True),
            Column('title', String, nullable=False),
            Column('description', String, nullable=True),
            Column('date', Date, nullable=False),
            Column('url', URLType, nullable=False),
            Column('video', URLType, nullable=False),
            Column('last_updated', DateTime, server_default=func.now(),
                   onupdate=func.now(), nullable=False),
        )

    @staticmethod
    def format_video_list(videos, fmt='psql'):
        """Create a formatted list of videos."""
        fields = ['ID', 'Date', 'Title', 'Description']
        table_data = [[
            video.video_id,
            video.date.strftime('%d %B %Y'),
            shorten(video.title, width=50),
            shorten(video.description, width=70)
        ] for video in videos]
        return tabulate(table_data, fields, tablefmt=fmt)

    def get_video(self, video_id):
        """Get video in database by ID."""
        video = self.db.query(self.model).get(video_id)
        if not video:
            self.manager.error(f'No video found for ID: {video_id}')
            return None
        return video

    @property
    def update(self):
        """Command to update the database with new videos."""
        @click.command(help='Updates the the list of videos.')
        @click.option('-l', '--list', 'list_', is_flag=True,
                      help='List any newly added minisodes')
        @click.option('-n', '--number', default=25, show_default=True,
                      help='Number of videos to retrieve from archive')
        @self.auto_login_user(with_account=True)
        def fn(account, number, list_):
            """Updates the the list of videos."""
            new_videos = self._update_videos(account.session_id, number)
            # Check for results
            if not new_videos:
                self.manager.info('No new videos found.')
                return
            # Print list of newly added videos
            self.manager.success(f'Added {len(new_videos)} new video(s)!')
            if list_:
                click.echo(self.format_video_list(new_videos))
        return fn

    @property
    def download(self):
        """Command to download a given video."""
        @click.command(help='Download a video by ID.')
        @click.option('-y', '--yes', is_flag=True,
                      help='Download without confirmation.')
        @click.option('-d', '--dest', type=click.Path(exists=True),
                      help='Folder to download file to.')
        @click.argument('video_id')
        @self.auto_login_user(with_account=True)
        def fn(video_id, yes, dest, account):
            """Download a video by ID."""
            video_path = self._get_download_dir(dest, account)
            video = self.get_video(video_id)
            if video:
                try:
                    self._download_video(video, video_path, yes)
                except RequestError as exc:
                    self.manager.error(str(exc))
        return fn

    @property
    def show(self):
        """Command to display video details."""
        @click.command(help='Show video details by ID')
        @click.argument('video_id')
        @self.auto_login_user()
        def fn(video_id):
            """Show video details by ID."""
            video = self.get_video(video_id)
            if video:
                form = u'{0:>15}: {1}'
                wrapper = TextWrapper(width=100,
                                      initial_indent='',
                                      subsequent_indent='                 ')
                description = '\n'.join(wrapper.wrap(video.description))
                video_data = '\n'.join([
                    form.format('ID', video.video_id),
                    form.format('Date', video.date.strftime('%d %B %Y')),
                    form.format('Title', video.title),
                    form.format('Description', description),
                    form.format('Video', video.video),
                    form.format('URL', video.url)
                ])
                click.echo(video_data)
        return fn

    @property
    def open(self):
        """Command to open video link in a browser."""
        @click.command(help='Open web page for video.')
        @click.argument('video_id')
        @self.auto_login_user()
        def fn(video_id):
            """Open web page for video."""
            video = self.get_video(video_id)
            if video:
                click.echo(f'Opening {video.url}')
                click.launch(video.url)
        return fn

    @property
    def list(self):
        """Command to display a list of videos."""
        @click.command(help='Show all available videos.')
        @click.option('-n', '--number', default=10, show_default=True,
                      help='Number of videos to get.')
        @click.option('-r', '--refresh', is_flag=True,
                      help='Update list of videos.')
        @click.option('-f', '--format', 'fmt', default='psql',
                      type=click.Choice(tabulate_formats), show_choices=False,
                      show_default=True, help='How to format the list.')
        @click.option('-s', '--search',
                      help='Search videos by title.')
        @self.auto_login_user(with_account=True)
        def fn(account, number, refresh, fmt, search=None):
            """Show all available videos."""
            if refresh:
                self._update_videos(account.session_id)
            # Set up query
            query = self.db.query(self.model) \
                .order_by(self.model.date.desc())
            # Handle search query
            if search:
                query = query.filter(self.model.title.like(f'%{search}%'))
            # Handle limit
            if number > 0:
                query = query.limit(number)
            # Run the query
            videos = query.all()
            if not videos:
                self.manager.warning('No videos found.')
                return
            # Display the list
            click.echo(self.format_video_list(videos, fmt=fmt))
        return fn
