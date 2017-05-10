import json
import sys
import os.path

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

import threading
import thread
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TIT3, TCON, TDAT, TALB, TCOM, TOPE, error
import Tkinter as tk
import tkFileDialog
import pygubu

CLIENT_ID = "" # Get your own client id

class myThread (threading.Thread):
    def __init__(self, tid, track_info, base_path, lock, parent):
        threading.Thread.__init__(self)
        self.id = tid
        self.track_info = track_info
        self.base_path = base_path
        self.lock = lock
        self.parent = parent
        self.success = False

    def run(self):
        (track_title, track_user, track_art, track_url) = self.track_info

        while True:
            self.lock.acquire()
            if self.parent.get_permission(self.id, track_title):
                self.lock.release()
                break
            self.lock.release()

        mp3_file = self.base_path + "/" + track_user + "/" + track_title + ".mp3"
            
        # Create artist folder if needed
        self.lock.acquire()
        if not os.path.exists(self.base_path + "/" + track_user):
            os.makedirs(self.base_path + "/" + track_user)
        self.lock.release()

        # Download song
        try:
            track_data = urlopen(track_url)
            target = open(mp3_file, "wb")
            target.write(track_data.read())
            target.close()
        except:
            self.lock.acquire()
            self.parent.update_prog(self.id, track_title, self.success)
            self.lock.release()
            return

        # Check if mp3 already has ID3 tags
        try:
            tags = ID3(mp3_file)
        except error:
            tags = ID3()

        # Download track art if it has any
        if track_art != None:
            tags["APIC"] = APIC(3, 'image/jpeg', 3, 'Front Cover', urlopen(track_art.replace("-large.jpg", "-t500x500.jpg")).read())
            
        # Set up other mp3 tags
        tags["TCOM"] = TCOM(3, track_user)  # Artist
        tags["TPE1"] = TPE1(3, track_user)  # Artist ??
        tags["TOPE"] = TOPE(3, track_user)  # Artist ?!?!?!
        tags["TALB"] = TALB(3, track_title) # Album (Use track title for unique images)
        tags["TIT2"] = TIT2(3, track_title) # Track title

        # V2_3 because Windows can't handle newer versions
        tags.save(mp3_file, v2_version=3)

        if os.path.isfile(mp3_file):
            self.success = True

        self.lock.acquire()
        self.parent.update_prog(self.id, track_title, self.success)
        self.lock.release()

class MYSC:
    def __init__(self, parent):
        self.parent = parent
        self.builder = builder = pygubu.Builder()
        builder.add_from_file('mysc.ui')
        self.mainwindow = builder.get_object('mainwindow', parent)
        builder.connect_callbacks(self)
        self.tree = self.builder.get_object('treeview_tracklist', self.mainwindow)
        self.status = self.builder.get_variable('status')
        self.progress_bar = self.builder.get_object('progressbar')
        self.client_id = CLIENT_ID
        self.cnt = 1
        self.clearURL = True
        self.appdata = os.getenv('APPDATA') + "/MYSC"
        self.tracks = dict()
        self.threads = dict()
        self.running = list()

    def on_button_select_clicked(self):
        for child in self.tree.get_children():
            self.tree.selection_add(child)

    def on_button_deselect_clicked(self):
        for child in self.tree.get_children():
            self.tree.selection_remove(child)

    def on_button_load_clicked(self):
        if len(self.running) > 0:
            print(self.running)
            return

        self.status.set('Looking up playlist...')
        playlist_url = self.builder.get_variable('playlist_url').get()
        
        thread.start_new_thread(self.parseTracks, (playlist_url,))
        # self.parseTracks(data)

    def get_permission(self, track_id, track_title):
        if len(self.running) < 8:
            self.running.append(track_id)
            # print(str(track_id) + "\t-\tDownloading..." + "\t-\t" + track_title)
            return True
        return False

    def update_prog(self, track_id, track_title, success):
        self.running.remove(track_id)

        if len(str(track_id)) < 8:
            printStr = str(track_id) + "\t\t|\t" + track_title + "\n"
        else:
            printStr = str(track_id) + "\t|\t" + track_title + "\n"

        if success:
            self.f.write(printStr)
        else:
            print(str(track_id) + "\t-\tDownload Failure" + "\t-\t" + track_title)

        self.progress_bar.step(self.progress_inc)
        self.progress_bar.update_idletasks()
        self.thread_cnt -= 1

        if self.thread_cnt == 0:
            self.progress_bar.stop()
            self.f.close()
            self.status.set('Finished')

    def on_download_clicked(self):
        if len(self.running) > 0:
            print(self.running)
            return
            
        self.status.set('Downloading tracks...')

        dirname = tkFileDialog.askdirectory(parent=self.parent,initialdir="/",title='Please select a download destination')

        if len(dirname ) <= 0:
            self.status.set("Invalid download destination")
            return

        base_path = dirname + "/" + self.playlist_title

        self.progress_inc = float(10000 / len(self.tree.selection()))
        self.thread_cnt = 0
        lock = threading.Lock()

        for selection in self.tree.selection():
            # thread.start_new_thread(this.download_song, (self.tracks[int(selection)], base_path))
            self.threads[int(selection)] = myThread(int(selection), self.tracks[int(selection)], base_path, lock, self)
            self.threads[int(selection)].start()
            self.thread_cnt += 1

    def parseTracks(self, playlist_url):
        try:
            full_url = "https://api.soundcloud.com/resolve?url=" + playlist_url + "&client_id=" + self.client_id
            resp = urlopen(full_url)
            data = json.loads(resp.read().decode('utf-8'))
        except:
            self.status.set("Invalid playlist")
            return

        # Get api-v2 of playlist
        try:
            full_url = data['uri'].replace("api", "api-v2") + "?client_id=" + self.client_id
            resp = urlopen(full_url)
            data = json.loads(resp.read().decode('utf-8'))
        except:
            self.status.set("No V2 For U")
            return

        self.playlist_title = data['title']
        self.track_count = int(data['track_count'])
        self.tracks_file = self.appdata + "/" + self.playlist_title + "/tracks.txt"

        if not os.path.exists(self.appdata + "/" + self.playlist_title):
            os.makedirs(self.appdata + "/" + self.playlist_title)

        # See what tracks are already downloaded
        if os.path.isfile(self.tracks_file):
            f = open(self.tracks_file, "r")
            for line in f:
                self.tracks[int(line.split()[0])] = "NoDL"
            f.close()

        self.f = open(self.tracks_file, "a")
        self.builder.get_variable('playlist_title').set(self.playlist_title)
        already_dl = 0
        self.status.set("Found " + str(self.track_count) + " tracks... Parsing data.")

        self.progress_inc = float(10000 / self.track_count)

        for track in data['tracks']:
            # Progress bar because this shit takes ages with api-v2
            self.progress_bar.step(self.progress_inc)
            self.progress_bar.update_idletasks()

            # Get the real JSON data with v2 api
            track_url = "https://api-v2.soundcloud.com/tracks/" + str(track['id']) + "?client_id=" + self.client_id
            try:
                track_resp = urlopen(track_url)
                track = json.loads(track_resp.read().decode('utf-8'))
            except:
                print("Loading the track with api-v2 didn't work, trying api-v1: " + track_url)

                try:
                    track_url = "https://api.soundcloud.com/tracks/" + str(track['id']) + "?client_id=" + self.client_id
                    track_resp = urlopen(track_url)
                    track = json.loads(track_resp.read().decode('utf-8'))
                except:
                    print("\tWell that didn't work either... rip")
                    self.track_count -= 1
                    continue


            # Make sure the track is... "Streamable"...
            if track['streamable'] == False:
                print("Track not streamable so can't download: " + track['title'])
                self.track_count -= 1
                continue

            track_title = track['title'].replace("\"", "").replace("*", "").replace("/", "").replace(":", "").replace("\\", "").replace(":", "")
            track_user = track['user']['username'].replace(":", "")
            track_art = track['artwork_url']
            track_id = track['id']
            track_url = "https://api.soundcloud.com/tracks/" + str(track['id']) + "/stream?client_id=" + self.client_id
            track_user = track_user.encode('ascii', 'ignore').strip()
            track_title = track_title.encode('ascii', 'ignore').strip()

            if not track_title:
                track_title = str(track_id)

            if track_id not in self.tracks:
                self.tree.insert('', 'end', iid=track_id, text=str(self.cnt), values=(track_title, track_user))
                self.tracks[track_id] = (track_title, track_user, track_art, track_url)
                self.cnt += 1
            else:
                already_dl += 1

        self.status.set("Found " + str(self.track_count) + " tracks, " + str(already_dl) + " already downloaded.")
        self.progress_bar.stop()

    def on_entry_playlist_url_focus(self):
        if self.clearURL:
            self.builder.get_variable('playlist_url').set("")
            self.clearURL = False

def main():
    root = tk.Tk()
    app = MYSC(root)
    root.mainloop()

if __name__ == '__main__':
    main()
