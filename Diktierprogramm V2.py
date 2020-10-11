import tkinter as tk
import multiprocessing
import concurrent.futures

# from google.cloud import speech_v1
from google.cloud import speech
import google.cloud.speech as gcs
from google.oauth2 import service_account


import datetime

import sys
import os
import io

import speech_recognition as SR

import time
import _queue

import shutil

# Programm quit function:
def quit_Diktierprogramm():

    print("In Quit")
    global GUI_obj
    global timer_handel

    # updateing info GUI:
    update_gui_config_queue.put(("status", "text", "Shutting Down..."), block=True)
    GUI_obj.update_gui()

    # stoping timer Process
    print("Stoping Timer")
    update_timer_queue.put({"quit": None}, block=True)
    timer_handel.join()

    # stoping listener process
    print("Stoping Listener")
    command_queue.put({"quit": None}, block=True)
    recognizer_handle.join()

    print("Stoping Recognizer")
    audio_data.put({"quit": None})

    GUI_obj.quit_gui()
    time.sleep(1)
    GUI_obj.main_window.destroy()



class GUI:
    def __init__(self, update_config_queue=None, cmd_queue=None, timer_queue=None):
        #update config: attribute, config_attribute, value, text_content

        self.main_window = tk.Tk()
        self.main_window.title("Google STT-API Diktierprogramm V0.1")

        # Layout Basics:
        # Here would be window widht, height, etc...

        # Layout Frames
        self.tool_bar_frame = tk.Frame(self.main_window)
        self.content_frame = tk.Frame(self.main_window)
        self.query_frame = tk.Frame(self.main_window)

        self.tool_bar_frame.pack(side=tk.TOP, fill=tk.X)
        self.content_frame.pack(side=tk.TOP)
        self.query_frame.pack(side=tk.BOTTOM)

        # Scrollable Text Field
        self.content_text = tk.Text(self.content_frame, height=35, width=100)
        self.content_scroll = tk.Scrollbar(self.content_frame)

        self.content_text.pack(side=tk.LEFT, fill=tk.Y)
        self.content_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.content_scroll.config(command=self.content_text.yview)
        self.content_text.config(yscrollcommand=self.content_scroll.set)

        # self.query_text.delete(0)
        # self.query_text.insert(tk.END, "Thing")

        # Query Field
        self.query_text = tk.Text(self.query_frame, height=10, width=100)
        self.query_text.pack(side=tk.BOTTOM, fill=tk.X)

        # placement of Buttons needs to be optimised

        # Toolbar
        self.time_label = tk.Label(self.tool_bar_frame, text="")
        self.time_label.pack(side=tk.RIGHT)

        self.status = tk.Label(self.tool_bar_frame, text="")
        self.status.pack(side=tk.RIGHT, fill=tk.X)

        self.stop_button = tk.Button(self.tool_bar_frame, text="Stop Recording")
        self.stop_button.bind("<Button-1>", self.stop)
        self.stop_button.pack(side=tk.LEFT, anchor=tk.W)

        self.start_button = tk.Button(self.tool_bar_frame, text="Start Recording")
        self.start_button.bind("<Button-1>", self.start)
        self.start_button.pack(side=tk.LEFT)

        # Dynamic Button - needs to be removed on condition.
        self.recognize_volume = tk.Button(self.tool_bar_frame, text="Calculate Nosise Floor")
        self.recognize_volume.bind("<Button-1>", self.calibrate_loudness)
        self.recognize_volume.pack(side=tk.LEFT)

        # IO Tasks
        self.__update_queue = update_config_queue
        self.update_timer_queue = timer_queue
        self.command_queue = cmd_queue

        # Controll Vars

        self.__run = True

        self.main_window.protocol("WM_DELETE_WINDOW", quit_Diktierprogramm)

    def start(self, event):
        self.status["text"] = "Translating"
        self.update_timer_queue.put({"message": "Remining Time in Query: ", "run_out_message": "Time ran out", "seconds":60}, block=True)
        self.command_queue.put({"recognize": True}, block=True)

    def stop(self, event):
        self.status["text"] = "Stopping Translation"
        self.command_queue.put({"recognize": False})
        self.update_timer_queue.put({"message": "", "seconds": 0},  block=True)
        self.update_timer_queue.put({"callback": ("status", "text", ""), "callback_seconds": 1}, block=True)


    def calibrate_loudness(self, event):
        self.status["text"] = "Be still, calibrating environment"
        self.update_timer_queue.put({"callback": ("status", "text", ""), "callback_seconds": 3, "message": "", "run_out_message": "", "seconds":0}, block=True)
        self.command_queue.put({"adjust_noise_floor": None}, block=True)


    def run_gui(self):
        while self.__run:
            self.update_gui()
            
    def quit_gui(self):
        self.__run = False

    def update_window_content(self):
        update = True
        while update:
            try:
                output = self.__update_queue.get(block=False)
                print(output)
                attr = getattr(self, output[0])
                attr[output[1]] = output[2]
            except _queue.Empty:
                update = False

    def update_gui(self):
        self.update_window_content()
        self.main_window.update()



class Timer:
    # Query: Keys: message, run_out_message, seconds, callback, callback_seconds, quit
    # message: message to be displayed while timer counts down
    # run_out_message: mesage to display once timer has reache zero
    # seconds: number of seconds to count down
    # callback: tuple of like config tuple, to reset 
    # callback_seconds: number of seconds till send of callback
    # quit if quit, kill process.
    
    def __init__(self, update_gui_config_queue, query_queue):
    
        self.update_gui_config_queue = update_gui_config_queue
        self.query_queue = query_queue
    
        self.counter = 3
        self.last_counter = 0
    
        self.message = "Test Message: "
        self.message_on_runout = "Test runout message"

        self.callback_counter = -1
        self.callback_query = {}


        self.run = True
    def run_timer(self):
        while self.run:
            update = True
            while update:
                try:
                    query = self.query_queue.get(block=False)

                    # remove for run:
                    print(query)
                    for key in enumerate(query.keys()):
                        if key[1] == "message":
                            self.message = query["message"]
                        if key[1] == "run_out_message":
                            self.message_on_runout = query["run_out_message"]
                        if key[1] == "seconds":
                            self.counter = query["seconds"]
                        if key[1] == "callback":
                            self.callback_query = query["callback"]
                        if key[1] == "callback_seconds":
                            self.callback_counter = query["callback_seconds"]
                        if key[1] == "quit":
                            self.run = False
                            break
                except _queue.Empty:
                    update = False

            if self.counter > 0:
                stop_update = False
                self.update_gui_config_queue.put(("time_label", "text", self.message + str(self.counter)))
            elif self.counter == 0 and self.last_counter == 1:
                self.update_gui_config_queue.put(("time_label", "text", self.message_on_runout))
            elif self.counter == 0 and self.last_counter == 0 and not stop_update:
                self.update_gui_config_queue.put(("time_label", "text", ""))
                stop_update = True

            if self.callback_counter == 0:
                self.update_gui_config_queue.put(self.callback_query)
    
    
            time.sleep(1)
            self.last_counter = self.counter
            if self.counter > 0:
                self.counter -= 1
            if self.callback_counter >= 0:
                self.callback_counter -= 1
    
        return None

class Listener:
    # command_queue: recognize, debug, set_config, get_config, quit, adjust_noise_floor
    # recognize: type bool. start / stop recognizer
    # debug: type bool. set debugging start / stop
    # get_config / set_config -> load config file, update config file.
    # quit: type None, stop process
    # adjust_noise_floor

    def __init__(self, command_queue, update_gui_config_queue, timer_query_queue, audio_data_queue, response_queue, debug=False):

        self.__command_queue = command_queue
        self.update_gui_queue = update_gui_config_queue
        self.timer_queue = timer_query_queue
        self.audio_data_queue = audio_data_queue
        self.response_queue = response_queue

        # parameters:
        self.debug = debug
        self.sample_frequency = 48000

        # not in use:
        # self.chunk_size = 1024
        # self.device_index = 0
        #
        # self.loudness_threshold = 300
        # self.dynamic_threshold = True
        # self.dynamic_threshold_dampening = 0.15
        # self.dynamic_threshold_adjustment_ratio = 1.5
        # self.pause_threshold = 0.8

        self.adjust_background_sound_duration = 2

        self.quit_listening_timeout = 10
        self.max_phrase_length = 60

        self.recognizer = SR.Recognizer()

        self.run = True

        self.keep_listening = False

        script_path = os.path.realpath(__file__)
        parrent_dir = os.path.abspath(os.path.join(script_path, os.pardir))
        
        self.wav_store_folder = os.path.join(parrent_dir, "_temp_wav") 
        
        # Removing previous audio files -> moving to trash
        if os.path.exists(self.wav_store_folder):
            shutil.rmtree(self.wav_store_folder)
            os.mkdir(self.wav_store_folder)
        elif not os.path.exists(self.wav_store_folder):
            os.mkdir(self.wav_store_folder)

    #if stop - last query needs to be removed.

    def run_listener(self):
        while self.run:
            read = True
            while read:
                try:
                    command = self.__command_queue.get(block=False)
                    print(command)
                    if type(command).__name__ == "dict":
                        for cmd in enumerate(command.keys()):
                            if cmd[1] == "recognize":
                                self.keep_listening = command["recognize"]
                            if cmd[1] == "adjust_noise_floor":
                                if  command["adjust_noise_floor"] is not None:
                                    self.adjust_background_sound_duration = command["adjust_noise_floor"]
                                    self.adjust_noise_floor()
                            if cmd[1] == "debug":
                                self.debug = command["debug"]
                            if cmd[1] == "get_config":
                                pass
                            if cmd[1] == "set_config":
                                pass
                            if cmd[1] == "quit":
                                self.run = False
                                break
                except _queue.Empty:
                    read = False

            if self.run == False:
                break

            response = True
            while response:
                try:
                    response_data = self.response_queue.get(block=False)
                    print(response_data)
                except _queue.Empty:
                    response = False

            if self.keep_listening:
                self.timer_queue.put({"seconds": 60}, block=True)
                self.listen()

        return None

    def adjust_noise_floor(self):
        with SR.Microphone(sample_rate=self.sample_frequency) as mic:
            self.recognizer.adjust_for_ambient_noise(source=mic, duration=self.adjust_background_sound_duration)
            print("Adjusted...")

    def listen(self):
        print("Listening")
        data_present = False
        try:
            with SR.Microphone(sample_rate=self.sample_frequency) as mic:
                data = self.recognizer.listen(source=mic, timeout=self.quit_listening_timeout, phrase_time_limit=self.max_phrase_length)
                data_present = True
        except SR.WaitTimeoutError:
            self.keep_listening = False

        # Saving sound_file temporary.
        if self.debug:
            current_datetime = datetime.datetime.now()
            
            # converting '2020-09-27 04:30:40.426022' to '2020.09.27_04-30-40'
            transform = str(current_datetime).split(".")[0].replace(" ", "_").replace("-", ".").replace(":", "-")
            saving_path = os.path.join(self.wav_store_folder, str(transform+ ".wav"))
            with open(saving_path, "wb") as file:
                audio_file = data.get_wav_data()
                file.write(audio_file)

        if data_present is True:
            print("Request put")
            just_data = data.get_wav_data()
            print(f"Length of data {len(just_data)}")
            self.audio_data_queue.put({"audio_bin": just_data}, block=True)


class Google_Cloud_STT_API:
    # audio_data_queue: audio_bin, sample_rate, language, config, dump, quit, index
    # audio_bin: binary data of Audio
    # sample_rate: sample rate of recorded audio
    # language: type string, language code
    # config - configuration data to set.
    # dump - dump configuratoin paramters
    # quit: None stop process
    # index: index of query

    # response: response_data, dump, index
    # response_data: the return object from the query
    # dump: return from the dump request
    # index: index of query
    def __init__(self, audio_data, response_data):
        self.audio_data_queue = audio_data
        self.response_data_queue = response_data

        self.encodings = [gcs.RecognitionConfig.AudioEncoding.LINEAR16,
                  gcs.RecognitionConfig.AudioEncoding.FLAC,
                  gcs.RecognitionConfig.AudioEncoding.AMR,
                  gcs.RecognitionConfig.AudioEncoding.AMR_WB,
                  gcs.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                  gcs.RecognitionConfig.AudioEncoding.MULAW,
                  gcs.RecognitionConfig.AudioEncoding.OGG_OPUS,
                  gcs.RecognitionConfig.AudioEncoding.SPEEX_WITH_HEADER_BYTE
                  ]

        self.sample_rate = 48000
        self.audio_binary_data = None
        self.language_code = "de-DE"
        self.query_index = 0
        self.request_timeout = 60
        self.run = True

        self.start_request = False

        self.request_config = None

        self.auth_path = "[PATH TO AUTH FILE]"

        # self.auth_obj = service_account.Credentials.from_service_account_file(self.auth_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=self.auth_path

        # self.google_recognizer = gcs.SpeechClient(credentials=self.auth_obj)
        self.google_recognizer = gcs.SpeechClient()

    def main_loop(self):
        while self.run:
            try:
                query = audio_data.get(block=False)
                for item in enumerate(query):
                    if item[1] == "audio_bin":
                        self.audio_binary_data = query["audio_bin"]
                        self.start_request = True
                    if item[1] == "sample_rate":
                        self.sample_rate = query["sample_rate"]
                    if item[1] == "language":
                        self.language_code = query["language"]
                    if item[1] == "config":
                        pass
                    if item[1] == "dump":
                        pass
                    if item[1] == "quit":
                        self.run = False
                        break
                    if item[1] == "index":
                        self.query_index = query["index"]
            except _queue.Empty:
                pass

            # config = {
            #     "language_code": self.language_code,
            #     "sample_rate_hertz": self.sample_rate,
            #     "encoding": encodings[0]
            # }
            self.request_config = gcs.RecognitionConfig(
                encoding=self.encodings[0],
                sample_rate_hertz=self.sample_rate,
                language_code=self.language_code
            )


            if self.start_request:
                print("Request sent to google")
                response = self.google_recognizer.recognize(config=config, audio=self.audio_binary_data, timeout=self.request_timeout)
                self.start_request = False

            self.response_data_queue.put({"response": response, "index": self.query_index})

        return None




if __name__ == '__main__':

    multi_manager = multiprocessing.Manager()

    update_gui_config_queue = multi_manager.Queue()
    update_timer_queue = multi_manager.Queue()
    command_queue = multi_manager.Queue()
    audio_data = multi_manager.Queue()
    response_data = multi_manager.Queue()

    command_queue.put({"recognize": False})

    # Timer Process
    count_down = Timer(update_gui_config_queue=update_gui_config_queue, query_queue=update_timer_queue)
    timer_handel = multiprocessing.Process(target=count_down.run_timer)
    timer_handel.start()

    # Recognizer Process
    recognizer_class = Listener(command_queue=command_queue, update_gui_config_queue=update_gui_config_queue, timer_query_queue=update_timer_queue, response_queue=response_data, audio_data_queue=audio_data)
    recognizer_handle = multiprocessing.Process(target=recognizer_class.run_listener)
    recognizer_handle.start()

    # Google Cloud Recognizer Thread
    google_cloud = Google_Cloud_STT_API(audio_data=audio_data, response_data=response_data)
    google_cloud_handle = multiprocessing.Process(target=google_cloud.main_loop)
    google_cloud_handle.start()

    # GUI instance
    GUI_obj = GUI(update_config_queue=update_gui_config_queue, timer_queue=update_timer_queue, cmd_queue=command_queue)
    GUI_obj.run_gui()
