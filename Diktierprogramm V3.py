# UPDATE: GUI wird jetzt multigethreaded => Geht nicht, GUI kann nicht gepickelt werden.

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

import speech_recognition as sr

import time
import _queue

import shutil


# Programm quit function:
def quit_diktierprogramm():
    print("MAIN:", "In Quit")
    global gui_obj
    global timer_handle

    # stopping gui
    update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                 "widget_attribute": "text",
                                                 "value": ""}})
    update_gui_config_queue.put({"update_dict": {"class_attribute": "status",
                                                 "widget_attribute": "text",
                                                 "value": "Shutting down..."}})
    gui_obj.update_gui()

    # stopping timer Process
    print("MAIN:", "Stopping Timer")
    update_timer_queue.put({"quit": None}, block=True)
    timer_handle.join()

    # stopping listener process
    print("MAIN:", "Stopping Listener")
    command_queue.put({"quit": None}, block=True)
    recognizer_handle.join()

    print("MAIN:", "Stopping Recognizer")
    # writing stop file.

    gui_obj.quit_gui()
    time.sleep(1)
    gui_obj.main_window.destroy()


class GUI:
    def __init__(self, update_config_queue=None, cmd_queue=None, timer_queue=None):
        # update config: update_dict, text_content, text_response, quit
        # update_dict: (class_attribute, widget_attribute, value)
        # text_content: text appended to main content text window
        # text_response: text replacing the text in the response window
        # quit: type None - quit main_loop

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
        self.recognize_volume = tk.Button(self.tool_bar_frame, text="Calculate Noise Floor")
        self.recognize_volume.bind("<Button-1>", self.calibrate_loudness)
        self.recognize_volume.pack(side=tk.LEFT)

        # IO Tasks
        self.__update_queue = update_config_queue
        self.update_timer_queue = timer_queue
        self.command_queue = cmd_queue

        # Controll Vars

        self.__run = True

        self.main_window.protocol("WM_DELETE_WINDOW", quit_diktierprogramm)

    def start(self, event):
        self.status["text"] = "Translating"
        self.update_timer_queue.put(
            {"message": "Remaining Time in Query: ", "run_out_message": "Time ran out", "seconds": 50}, block=True)
        self.command_queue.put({"recognize": True}, block=True)

    def stop(self, event):
        self.status["text"] = "Stopping Translation"
        self.time_label["text"] = ""
        self.command_queue.put({"recognize": False})
        self.update_timer_queue.put({"message": "", "seconds": 0}, block=True)
        self.update_timer_queue.put({"callback": {"update_dict": {"class_attribute": "status",
                                                                  "widget_attribute": "text", "value": ""}},
                                     "callback_seconds": 1}, block=True)

    def calibrate_loudness(self, event):
        self.status["text"] = "Be still, calibrating environment"
        self.update_timer_queue.put(
            {"callback": {"update_dict": {"class_attribute": "status", "widget_attribute": "text", "value": ""}},
             "callback_seconds": 3, "message": "", "run_out_message": "", "seconds": 0}, block=True)
        self.command_queue.put({"adjust_noise_floor": None}, block=True)

    def run_gui(self):
        while self.__run:
            self.update_gui()

    def update_window_content(self):
        update = True
        while update:
            try:
                query = self.__update_queue.get(block=False)

                # remove for run:
                print("GUI:", query)
                for key in enumerate(query.keys()):
                    if key[1] == "update_dict":
                        update_dict = query["update_dict"]
                        attribute = getattr(self, update_dict["class_attribute"])
                        attribute[update_dict["widget_attribute"]] = update_dict["value"]
                    elif key[1] == "text_content":
                        pass
                    elif key[1] == "text_response":
                        pass
                    elif key[1] == "quit":
                        self.__run = False
                        break
                    else:
                        print("GUI:", f"GUI got unexpected key: {key[1]}")
            except _queue.Empty:
                update = False

    def update_gui(self):
        self.update_window_content()
        self.main_window.update()

    def quit_gui(self):
        self.__run = False


class Timer:
    # Query Keys: message, run_out_message, seconds, callback, callback_seconds, quit
    # message: message to be displayed while timer counts down
    # run_out_message: mesage to display once timer has reache zero
    # seconds: number of seconds to count down
    # callback: tuple of like config tuple, to reset
    # callback_seconds: number of seconds till send of callback
    # quit if quit, kill process.

    def __init__(self, update_gui_queue, query_queue):

        self.update_gui_config_queue = update_gui_queue
        self.query_queue = query_queue

        self.counter = 3
        self.last_counter = 0

        self.message = "Test Message: "
        self.message_on_runout = "Test runout message"

        self.callback_counter = -1
        self.callback_query = {}

        self.run = True
        self.stop_update = False

    def run_timer(self):
        stop_update = False
        while self.run:
            update = True
            while update:
                try:
                    query = self.query_queue.get(block=False)

                    # remove for run:
                    print("TIMER:", query)
                    for key in enumerate(query.keys()):
                        if key[1] == "message":
                            self.message = query["message"]
                        elif key[1] == "run_out_message":
                            self.message_on_runout = query["run_out_message"]
                        elif key[1] == "seconds":
                            self.counter = query["seconds"]
                        elif key[1] == "callback":
                            self.callback_query = query["callback"]
                        elif key[1] == "callback_seconds":
                            self.callback_counter = query["callback_seconds"]
                        elif key[1] == "quit":
                            self.run = False
                            break
                        else:
                            print("TIMER:", f"Timer got unexpected argument: {key[1]}")
                except _queue.Empty:
                    update = False

            if self.counter > 0:
                stop_update = False
                self.update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                                  "widget_attribute": "text",
                                                                  "value": self.message + str(self.counter)}})
            elif self.counter == 0 and self.last_counter == 1:
                self.update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                                  "widget_attribute": "text",
                                                                  "value": self.message_on_runout}})

            elif self.counter == 0 and self.last_counter == 0 and (not stop_update):
                self.update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                                  "widget_attribute": "text",
                                                                  "value": ""}})
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

    def __init__(self, cmd_queue, update_gui_queue, timer_query_queue, debug=False):

        self.__command_queue = cmd_queue
        self.update_gui_queue = update_gui_queue
        self.timer_queue = timer_query_queue

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
        self.max_phrase_length = 50

        self.recognizer = sr.Recognizer()

        self.run = True

        self.keep_listening = False

        script_path = os.path.realpath(__file__)
        parent_dir = os.path.abspath(os.path.join(script_path, os.pardir))

        # transfer locations
        self.wav_store_folder = os.path.join(parent_dir, "_temp_wav")
        self.txt_store_folder = os.path.join(parent_dir, "_temp_txt")

        # Request variables
        self.request_index = 0
        self.wav_path = None
        self.done_path = None
        self.folder = None

        # Removing previous audio files -> moving to trash
        if os.path.exists(self.wav_store_folder):
            shutil.rmtree(self.wav_store_folder)
            os.mkdir(self.wav_store_folder)
        elif not os.path.exists(self.wav_store_folder):
            os.mkdir(self.wav_store_folder)

        print("LISTENER:", f"Made {self.wav_store_folder}")

        # Removing previous text files -> moving to trash
        if os.path.exists(self.txt_store_folder):
            shutil.rmtree(self.txt_store_folder)
            os.mkdir(self.txt_store_folder)
        elif not os.path.exists(self.txt_store_folder):
            os.mkdir(self.txt_store_folder)
        print("LISTENER:", f"Made {self.txt_store_folder}")

    # if stop - last query needs to be removed.
    def run_listener(self):
        while self.run:

            self.start_recognition()

            read = True
            while read:
                try:
                    command = self.__command_queue.get(block=False)
                    print("LISTENER:", command)
                    if type(command).__name__ == "dict":
                        for cmd in enumerate(command.keys()):
                            if cmd[1] == "recognize":
                                self.keep_listening = command["recognize"]
                            elif cmd[1] == "adjust_noise_floor":
                                if command["adjust_noise_floor"] is not None:
                                    self.adjust_background_sound_duration = command["adjust_noise_floor"]
                                    self.adjust_noise_floor()
                            elif cmd[1] == "debug":
                                self.debug = command["debug"]
                            elif cmd[1] == "get_config":
                                pass
                            elif cmd[1] == "set_config":
                                pass
                            elif cmd[1] == "quit":
                                self.run = False
                                self.keep_listening = False
                                break
                            else:
                                print("LISTENER:", f"Listener got unexpected argument: {cmd[1]}")
                except _queue.Empty:
                    read = False

            if self.run is not True:
                break

            if self.keep_listening:
                self.timer_queue.put({"seconds": self.max_phrase_length}, block=True)
                self.listen()

        return None

    def adjust_noise_floor(self):
        with sr.Microphone(sample_rate=self.sample_frequency) as mic:
            self.recognizer.adjust_for_ambient_noise(source=mic, duration=self.adjust_background_sound_duration)
            print("LISTENER:", "Adjusted...")

    def listen(self):
        print("LISTENER:", "Listening")
        data_present = False
        try:
            with sr.Microphone(sample_rate=self.sample_frequency) as mic:
                data = self.recognizer.listen(source=mic, timeout=self.quit_listening_timeout,
                                              phrase_time_limit=self.max_phrase_length)
                data_present = True
        except sr.WaitTimeoutError:
            print("LISTENER:", "To Silent")
            self.update_gui_queue.put({"update_dict": {"class_attribute": "status", "widget_attribute": "text",
                                                       "value": "No speech. Stopping recognition..."}})
            self.timer_queue.put({"seconds": 0, "message": "", "run_out_message": ""})
            self.timer_queue.put({"callback": {"update_dict": {"class_attribute": "status",
                                                               "widget_attribute": "text",
                                                               "value": ""}},
                                  "callback_seconds": 3})
            self.keep_listening = False

        if data_present is True:
            audio_data = data.get_wav_data()

            self.folder = os.path.join(self.wav_store_folder, str(self.request_index))

            self.wav_path = os.path.join(self.folder, str(self.request_index) + ".wav")

            # self.wav_config_path = os.path.join(self.folder, str(self.request_index) + ".json")

            self.done_path = os.path.join(self.folder, str(self.request_index) + ".txt")

            if not os.path.exists(self.folder):
                os.mkdir(self.folder)

            else:
                print("LISTENER:", "Folder exists already, overwriting existing folder")
                shutil.rmtree(self.foler)

                os.mkdir(self.folder)

            # writing audio data
            with io.open(self.wav_path, "wb") as file:
                file.write(audio_data)

            # writing config_data
            # config_dict = {}
            print("LISTENER:", "using defaults for config, config file not implemented.")

            self.request_index += 1

    def start_recognition(self):
        if self.keep_listening and self.done_path is not None:
            with open(self.done_path, "w") as file:
                file.write("Done")
            self.folder = None
            self.wav_path = None
            self.done_path = None
        elif self.keep_listening is False and self.done_path is not None:
            shutil.rmtree(self.folder)
            self.folder = None
            self.done_path = None
            self.wav_path = None
            self.request_index -= 1


class GoogleCloudSTTAPI:
    def __init__(self):
        # Folders need to be filled

        script_path = os.path.realpath(__file__)
        parent_dir = os.path.abspath(os.path.join(script_path, os.pardir))

        self.log_file = os.path.join(parent_dir, "log_Request_Script.txt")
        self.input_folder = os.path.join(parent_dir, "_temp_wav")
        self.output_folder = os.path.join(parent_dir, "_temp_txt")

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
        self.query_index = ""
        self.request_timeout = 60
        self.run = True

        self.start_request = False
        self.overwrite_request_config = True
        self.current_config = None
        self.default_config = gcs.RecognitionConfig(
            {"encoding": self.encodings[0],
             "sample_rate_hertz": self.sample_rate,
             "language_code": self.language_code
             }

        )

        self.response = None
        self.response_dict = {}

        self.auth_path = "C:/Users/AliSot2000/Documents/Google_Cloud/tribal-sunbeam-286522-d7283289ed2b.json"
        self.auth_path = "[PATH TO AUTH FILE FROM GOOGLE]"


        # other version to get the auth file loaded...
        # self.auth_obj = service_account.Credentials.from_service_account_file(self.auth_path)
        # self.google_recognizer = gcs.SpeechClient(credentials=self.auth_obj)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.auth_path
        self.google_recognizer = gcs.SpeechClient()

        self.debug = False

    def main_loop(self):
        while self.run:
            # query folders: folders containing queries as a wav file, a txt file and a json file.
            query_folders = os.listdir(self.input_folder)
            if len(query_folders) > 0:
                for folder in query_folders:
                    query_file_path = os.path.join(self.input_folder, folder)
                    if os.path.isdir(query_file_path) and "_" not in os.path.basename(query_file_path):
                        self.query_index = os.path.basename(query_file_path)
                        files = os.listdir(query_file_path)
                        if len(files) == 2:
                            for file in files:
                                if os.path.splitext(file)[1] == ".wav":
                                    with io.open(os.path.join(query_file_path, file), "rb") as wav_file:
                                        data = wav_file.read()
                                        self.audio_binary_data = gcs.RecognitionAudio(content=data)
                                        self.start_request = True
                            if self.overwrite_request_config:
                                self.current_config = self.default_config
                            else:
                                print("not implemented yet")

                            if self.start_request:
                                print("Request sent to google")
                                try:
                                    self.response = self.google_recognizer.recognize(config=self.current_config,
                                                                                     audio=self.audio_binary_data,
                                                                                     timeout=self.request_timeout)
                                    self.write_response(response_path=os.path.join(self.output_folder,
                                                                                   str(self.query_index + ".json")))
                                    print(self.response)
                                except Exception as e:
                                    with open(self.log_file, "w") as log:
                                        print(f"An Exception occurred:\n:{e}")
                                        log.write(f"An Exception occurred:\n{e}")

                                self.start_request = False

                            if not self.debug:
                                shutil.rmtree(query_file_path)
                                print("removed File")
                            else:
                                print(f"new path: {str(query_file_path + '_debug')}")
                                shutil.move(query_file_path, str(query_file_path + '_debug'))

                    elif os.path.isfile(query_file_path):
                        if os.path.basename(query_file_path) == "quit.txt":
                            self.run = False
                            os.remove(query_file_path)
                            print("Quit")
                        elif os.path.basename(query_file_path) == "config.txt":
                            os.remove(query_file_path)
                            print("updating config...")

        return None

    def response_to_string(self):
        self.response_dict = {"results": []}
        for result in self.response.results:
            result_dict = {"alternatives": []}
            for alternative in result.alternatives:
                alternative_dict = {"transcript": alternative.transcript, "confidence": alternative.confidence,
                                    "words": []}

                for word in alternative.words:
                    word_dict = {"startTime": word.start_time, "endTime": word.end_time,
                                 "word": word.word, "speakerTag": word.speaker_tag}
                    alternative_dict["words"].append(word_dict)

                result_dict["alternatives"].append(alternative_dict)

            try:
                result_dict["channelTag"] = result.channelTag
            except AttributeError:
                print("No channelTag present...")
            except Exception as e:
                with open(self.log_file, "w") as file:
                    file.write(f"An Exception Occured: \n{e}")
                print(e)
            self.response_dict["results"].append(result_dict)

        print(self.response_dict)

    def write_response(self, response_path):
        if self.response is not None:
            self.response_to_string()
            with open(response_path, "w") as file:
                json.dump(self.response_dict, file, indent=4)


if __name__ == '__main__':
    multi_manager = multiprocessing.Manager()

    update_gui_config_queue = multi_manager.Queue()
    update_timer_queue = multi_manager.Queue()
    command_queue = multi_manager.Queue()

    # Timer Process
    count_down = Timer(update_gui_queue=update_gui_config_queue, query_queue=update_timer_queue)
    timer_handle = multiprocessing.Process(target=count_down.run_timer)
    timer_handle.start()

    # Recognizer Process
    recognizer_class = Listener(cmd_queue=command_queue, update_gui_queue=update_gui_config_queue,
                                timer_query_queue=update_timer_queue)
    recognizer_handle = multiprocessing.Process(target=recognizer_class.run_listener)
    recognizer_handle.start()

    # Comment this for the running version.
    google = GoogleCloudSTTAPI()
    google_handle = multiprocessing.Process(target=google.main_loop)
    google_handle.start()

    # GUI Thread
    print("MAIN:", "Starting GUI")
    gui_obj = GUI(update_config_queue=update_gui_config_queue, cmd_queue=command_queue, timer_queue=update_timer_queue)
    gui_obj.run_gui()

