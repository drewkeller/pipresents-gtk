import mpv
import gc
import os
import threading
from multiprocessing import Process
import time

from pp_utils import Monitor

""""
Interesting references
    * https://github.com/jaseg/python-mpv/
    * https://github.com/jaseg/python-mpv/blob/main/mpv.py
    * https://github.com/jaseg/python-mpv/issues/222
    * https://github.com/jaseg/python-mpv/issues/88
    * https://github.com/trin94/python-mpv-gtk4
"""

class TaskType:
    FOREGROUND = 0
    THREAD = 1
    PROCESS = 2

def my_log(loglevel, component, message):
    "MPV uses this function as log output but it is more verbose than we want for the memory test."
    # print('[{}] {}: {}'.format(loglevel, component, message))
    pass

def play_media_list(mon, media_list, task_type, previous_rss=-1):
    previous_rss = mon.mem(None, f"Uncollected: {gc.collect():5}    ", previous_rss)
    for media_item in media_list:
        media = f"/home/pi/pp_home/media/{media_item}"
        match task_type:
            case TaskType.FOREGROUND:
                play_in_foreground(media)
            case TaskType.THREAD:
                play_in_thread(media)
            case TaskType.PROCESS:
                play_in_process(media)

def play_in_foreground(media):
    "Play a file in the main thread"
    play_a_file(media)

def play_in_thread(media):
    "Create a thread and wait for it to finish"
    player_thread = threading.Thread(target=lambda: play_a_file(media))
    player_thread.start()
    player_thread.join()

def play_in_process(media):
    "Create a child process and wait for it to finish"
    global in_process_log_file
    player_process = Process(target=lambda: play_a_file(media, in_process_log_file, do_append=True))
    player_process.start()
    player_process.join()

def create_player() -> mpv.MPV:
    "Create a new MPV player instance"
    player = mpv.MPV(log_handler=my_log, ytdl=True, input_default_bindings=True, input_vo_keyboard=True)
    # Option access, in general these require the core to reinitialize
    player['vo'] = 'gpu'
    return player

def play_a_file(media, log_file=None, do_append=True):
    "This is the common 'play' method"
    player = create_player()
    player.play(media)
    player.wait_for_playback()
    player.terminate()
    while not player.core_shutdown:
        time.sleep(.05)
    del player
    if log_file:
        mon = Monitor(global_log_level=31, class_log_level=31, log_file=log_file, do_append=do_append)
        mon.mem(None, f"Uncollected: {gc.collect():5}    ")

# avoid messages about not having the locale set
import locale
locale.setlocale(locale.LC_NUMERIC, 'C')

current_dir = os.path.dirname(os.path.abspath(__file__))
in_process_log_file=f"{current_dir}/pp_logs/pp_log_in-process.txt"
if os.path.exists(in_process_log_file):
    os.remove(in_process_log_file)

mon = Monitor(global_log_level=31, class_log_level=31, log_file=f"{current_dir}/pp_logs/pp_log.txt")
mon.log(None, "Started")

# Add more filenames from pp_home/media/ if desired
media_list = { "1sec.mp4" }

# uncomment one of the following
#task_type = TaskType.FOREGROUND
#task_type = TaskType.THREAD
task_type = TaskType.PROCESS
while True:
    play_media_list(mon, media_list, task_type)
