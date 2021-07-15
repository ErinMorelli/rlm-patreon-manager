# rlm-patreon-manager

A CLI tool for viewing and downloading RLM Patreon exclusive content.

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ErinMorelli_rlm-patreon-manager&metric=alert_status)](https://sonarcloud.io/dashboard?id=ErinMorelli_rlm-patreon-manager)

---
### Installation

Clone the repo and install using the setup.py file.

```
$ python setup.py install
```

### Usage

Access the manager using the `rlm-patreon` command.

```
$ rlm-patreon
Usage: rlm-patreon [OPTIONS] COMMAND [ARGS]...

  Manage Patreon exclusive content.

Options:
  --help  Show this message and exit.

Commands:
  account    Manage your Patreon account.
  videos     Manage Patreon exclusive videos.
```


### Setup

Login to your RLM Patreon account before using the manager the first time.

```
$ rlm-patreon account login
Email: example@email.com
Password:
Repeat for confirmation:
Successfully logged in!
```

You'll need to run the update command for each content type to populate the database, for example:

```
$ rlm-patreon videos update
Scanning for new videos: 100%|███████████████████████████████████████████████| 25/25 videos
Added 25 new video(s)!
```

### List Content

Display a list of all content by type.

```
$ rlm-patreon videos list
+------+------------------+--------------------------------------------------+----------------------------------------------------------------------+
|   ID | Date             | Title                                            | Description                                                          |
|------+------------------+--------------------------------------------------+----------------------------------------------------------------------|
|    1 | 12 July 2021     | Wheel of the Worst #22 Outtakes                  |                                                                      |
|    2 | 06 June 2021     | BOTW 101 Outtakes                                |                                                                      |
|    3 | 04 June 2021     | True Lies Voice Over Man                         | I had to dig up the file of this video for this new BOTW, so I [...] |
|    4 | 17 May 2021      | Rich Evans Watches Weber Cooks                   |                                                                      |
|    5 | 12 May 2021      | Star Trek Trivia Outtakes                        |                                                                      |
|    6 | 06 April 2021    | Best of the Worst 99/Half in the Bag 191Outtakes |                                                                      |
|    7 | 14 March 2021    | 10 Year Anniversary Outtakes                     |                                                                      |
|    8 | 22 February 2021 | Blood Shack Outtakes                             |                                                                      |
|    9 | 02 February 2021 | Dustin Diamond interview                         | Way back on only our third episode of Half in the Bag, fellow [...]  |
|   10 | 31 January 2021  | SpaceJacked BTS Video                            | A quick look at the making of the Spacejacked ending to the [...]    |
+------+------------------+--------------------------------------------------+----------------------------------------------------------------------+
```

### Show Content Info

Display info about a specific piece of content.

```
$ rlm-patreon videos show 3
             ID: 3
           Date: 04 June 2021
          Title: True Lies Voice Over Man
    Description: I had to dig up the file of this video for this new BOTW, so I thought I'd make a reel of all the
                 nasty nasty song lyrics being read by the voice over man. Enjoy!
          Video: https://vimeo.com/558336763
            URL: https://www.patreon.com/posts/true-lies-voice-52110362
```

### Download Content

Download a file to your local drive.

```
$ rlm-patreon videos download 1
Download file to /Users/username/Videos/BOTW 22 Outtakes.mp4? [y/N]: y
BOTW 22 Outtakes.mp4: 100%|██████████████████████████████████████████| 254697/254697 [00:01<00:00, 13426.97KB/s]
```

By default files will be downloaded to user's home directory, but you can change the default destination for your account.

```
$ rlm-patreon account update --download_dir /path/to/destination
```

Or set the destination on a per-download basis:

```
$ rlm-patreon videos download 1 --dest /path/to/destinaton
```

### Open Content Link

Use the open command to launch the original content page on the RLM website in a browser.

```
$ rlm-patreon videos open 1
Opening https://www.patreon.com/posts/wheel-of-worst-53603542
```

### Help

You can always view the options for commands using the `--help` flag.

```
$ rlm-patreon videos --help
Usage: rlm-patreon videos [OPTIONS] COMMAND [ARGS]...

  Manage Patreon exclusive minisodes.

Options:
  --help  Show this message and exit.

Commands:
  download  Download a video by ID.
  list      Show all available videos.
  open      Open web page for video.
  show      Show video details by ID.
  update    Updates the the list of videos.
```
