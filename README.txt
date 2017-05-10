Download Python from https://www.python.org/downloads/

During installation, you are given an option to add python.exe to PATH. Check that box.

Open a terminal and type 'pip install mutagen' then 'pip install pygubu'. These are python libraries needed to run the script.

Must supply your own client_id for any access to SoundCloud's api. 

Script will parse through a playlist and attempt to download songs using SoundCloud's api. Somewhat recent SoundCloud changes have made it easier for artists to prevent this from happening so expect some to be missed.

Songs that are downloaded from a playlist are tracked and saved to the Appdata folder. Running the script over the same playlist at a later date will only attempt to download new songs.
