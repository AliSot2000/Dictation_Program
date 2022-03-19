# UPDATE: GUI wird jetzt multigethreaded => Geht nicht, GUI kann nicht gepickelt werden.
# try using different version of python to run with correct functioning

import tkinter as tk
import multiprocessing

# from google.cloud import speech_v1
from google.cloud import speech
import google.cloud.speech as gcs
from google.oauth2 import service_account

import os
import io
import subprocess
import threading

import speech_recognition as sr

import time
import _queue

import shutil
import json
quit_path_request_script = ""


def retdebg(instring):
    print(f"RETRIEVER: {instring}")


def run_bach_requst_script():
    file_path = os.path.abspath(__file__)
    root_dir = os.path.abspath(os.path.join(file_path, os.pardir, os.pardir))
    bash_script_path = os.path.abspath(os.path.join(root_dir, "bash", "request_script_run.bash"))

    print("MAIN:", "Running Script")
    subprocess.Popen(bash_script_path, shell=True)


# Program quit function:
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

    print("MAIN:", "Stopping Recognizer with file")
    with open(os.path.join(quit_path_request_script, "quit.txt"), "w") as quit_file:
        quit_file.write("quit")
    # writing stop file.

    print("MAIN:", "Stopping Retriever with file")
    with open(os.path.join(quit_path_retriever, "quit.txt"), "w") as quit_file:
        quit_file.write("Quit")
    retriever_handle.join()

    print("MAIN: QUITING GUI")
    terminal_handle.join()

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
        self.content_text = tk.Text(self.content_frame, height=35, width=100, wrap=tk.WORD)
        self.content_scroll = tk.Scrollbar(self.content_frame)

        self.content_text.pack(side=tk.LEFT, fill=tk.Y)
        self.content_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.content_scroll.config(command=self.content_text.yview)
        self.content_text.config(yscrollcommand=self.content_scroll.set)

        # self.query_text.delete(0)
        # self.query_text.insert(tk.END, "Thing")

        # Query Field
        self.query_text = tk.Text(self.query_frame, height=10, width=100, wrap=tk.WORD)
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
        self.remove_double_spaces = False

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
                        content = ""
                        content = self.content_text.get("1.0", tk.END)
                        content += query["text_content"]

                        if self.remove_double_spaces:
                            content.replace("  ", " ")
                            self.content_text.delete("1.0", tk.END)
                            self.content_text.insert(tk.END, content)
                        else:
                            self.content_text.insert(tk.END, query["text_content"])

                    elif key[1] == "text_response":
                        self.query_text.delete("1.0", tk.END)
                        self.query_text.insert(tk.END, query["text_response"])
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
    # run_out_message: message to display once timer has reache zero
    # seconds: number of seconds to count down
    # callback: tuple of like config tuple, to reset
    # callback_seconds: number of seconds till send of callback
    # quit if quit, kill process.

    def __init__(self, update_gui_queue, query_queue):

        self.update_gui_config_queue = update_gui_queue
        self.query_queue = query_queue

        self.counter = 0
        self.last_counter = 0

        self.message = ""
        self.message_on_runout = ""

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
            # count down to 1
            if self.counter > 0:
                stop_update = False
                self.update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                                  "widget_attribute": "text",
                                                                  "value": self.message + str(self.counter)}})
            # run out message
            elif self.counter == 0 and self.last_counter == 1:
                self.update_gui_config_queue.put({"update_dict": {"class_attribute": "time_label",
                                                                  "widget_attribute": "text",
                                                                  "value": self.message_on_runout}})
            # remove timer
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

    def __init__(self, cmd_queue, update_gui_queue, timer_query_queue, debug=True):

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
                    else:
                        print("LISTENER:", "Command needs to be Dict")
                except _queue.Empty:
                    read = False

            if self.run is not True:
                break

            if self.keep_listening:
                self.timer_queue.put({"message": "Remaining Time in Query: ", "run_out_message": "Time ran out",
                                      "seconds": 50}, block=True)
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
            self.timer_queue.put({"message": "", "seconds": 0, "run_out_message": ""})
            self.update_gui_queue.put({"update_dict": {"class_attribute": "time_label",
                                                       "widget_attribute": "text",
                                                       "value": "sending Request to google..."}})
            audio_data = data.get_wav_data()

            self.folder = os.path.join(self.wav_store_folder, str(self.request_index))

            self.wav_path = os.path.join(self.folder, str(self.request_index) + ".wav")

            # self.wav_config_path = os.path.join(self.folder, str(self.request_index) + ".json")

            self.done_path = os.path.join(self.folder, str(self.request_index) + ".txt")

            if not os.path.exists(self.folder):
                os.mkdir(self.folder)

            else:
                print("LISTENER:", "Folder exists already, overwriting existing folder")
                shutil.rmtree(self.folder)

                os.mkdir(self.folder)

            # writing audio data
            with io.open(self.wav_path, "wb") as file:
                file.write(audio_data)

            # writing config_data
            # config_dict = {}
            print("LISTENER:", "using defaults for config, config file not implemented.")

            self.request_index += 1

            self.update_gui_queue.put({"update_dict": {"class_attribute": "time_label",
                                                       "widget_attribute": "text",
                                                       "value": ""}})

    def start_recognition(self):
        if self.keep_listening and self.done_path is not None:
            with open(self.done_path, "w") as file:
                file.write("Done")
            self.folder = None
            self.wav_path = None
            self.done_path = None
            print("LISTENER:", "Still listening, writing done file")
        elif self.keep_listening is False and self.done_path is not None:
            shutil.rmtree(self.folder)
            self.folder = None
            self.done_path = None
            self.wav_path = None
            # self.request_index -= 1
            print("LISTENER:", "No longer listening, deleting tree")

    def get_wave_store_path(self):
        return self.wav_store_folder

    def get_txt_store_path(self):
        return self.txt_store_folder


class RetrieveText:
    def __init__(self, gui_queue, search_path, debug=True):
        self.gui_update_queue = gui_queue
        self.search_path = os.path.abspath(search_path)

        self.use_defaults = True
        self.config_path = None

        self.debug = debug
        self.debug_folder = os.path.join(self.search_path, "_debug")

        self.caps_lock = False
        self.response_dict = None
        self.response_string = ""

        self.result = ""
        self.work_result = ""
        self.processed_result = ""

        self.locate_commands = True

        self.stop_counter = 0
        self.stop_index = None

        self.__run = True

        # self.future_default_config = {
        #     "escape_word": "stop",
        #     "replacement_dict": {
        #         "neue zeile": "\n",
        #         "zeilenumbruch": "\n",
        #         "doppelpunkt": ":",
        #         "semikolon": ";",
        #         "strichpunkt": ";",
        #         "anführungszeichen": "'",
        #         "schlusszeichen": "'",
        #         "komma": ","
        #     },
        #     "caps_lock_word": "caps-lock",
        #     "gross_schreibung": "gross"
        # }

        self.default_config_dict = {
            "escape_word": "stopp",
            "simple_replacement_list": [
                ["\n", "neue zeile", 2],
                ["\n", "zeilenumbruch", 2],
                ["\n", "neue linie", 2],
                ["/", "schrägstrich", 3],
                [":", "doppelpunkt", 1],
                [";", "semikolon", 1],
                [";", "strichpunkt", 1],
                ["(", "klammer auf", 2],
                [")", "klammer zu", 1],
                ["-", "bindestrich", 3],
                [">", "grösser als", 3],
                ["<", "kleiner als", 3]
            ],
            "general_replaces": {"ß": "ss"},
            "caps_lock_word": "caps-lock",
            "capital_writing": "gross"
        }

        self.config_dict = self.default_config_dict

        if self.use_defaults is not True:
            parent_dir = os.path.abspath(os.path.join(__file__, os.pardir))
            self.config_path = os.path.join(parent_dir, "Retrieve_Text_config.json")

            self.config_dict = json.load(self.config_path)

        # Adding Debug folder
        if self.debug:
            if os.path.exists(self.debug_folder):
                print("RETRIEVER:", "Old debug path exists, removing path")
                shutil.rmtree(self.debug_folder)
            os.mkdir(self.debug_folder)

    def run_retriever(self):
        self.__run = True
        while self.__run:
            # reseting variables:
            self.result = ""

            files = os.listdir(self.search_path)
            data_present = False
            for file in files:
                file_name = os.path.splitext(file)[0]
                if file_name.isdecimal():
                    try:
                        with open(os.path.join(self.search_path, file), "r") as json_file:
                            self.response_dict = json.load(json_file)
                            json_file.seek(0)
                            self.response_string = json_file.read()
                            data_present = self.get_translation()
                    except Exception as e:
                        print(f"An Exception occured: {e}")

                    if data_present:
                        # adding spaces to beginning and end of String.
                        if self.locate_commands:
                            # recognizing commands
                            self.complex_replacement()
                            # adding results to gui
                            self.gui_update_queue.put({"text_content": self.processed_result,
                                                       "text_response": self.response_string})
                        else:
                            self.gui_update_queue({"text_content": self.result,
                                                     "text_response": self.response_string})

                        if self.debug:
                            print("RETRIEVER:", "Moved Result to debug folder")
                            shutil.move(os.path.join(self.search_path, file),
                                        os.path.join(self.debug_folder, file))
                        else:
                            os.remove(os.path.join(self.search_path, file))

                if file_name == "quit":
                    os.remove(os.path.join(self.search_path, file))
                    print("RETRIEVER:", "Stop Runner")
                    self.__run = False
                    break
        return None

    # def run_simple_retriever(self):
    #     self.__run = True
    #     while self.__run:
    #         files = os.listdir(self.search_path)
    #         data_present = False
    #         for file in files:
    #             file_name = os.path.splitext(file)[0]
    #             if file_name.isdecimal():
    #                 try:
    #                     with open(os.path.join(self.search_path, file), "r") as json_file:
    #                         self.response_dict = json.load(json_file)
    #                         json_file.seek(0)
    #                         self.response_string = json_file.read()
    #                         data_present = self.get_translation()
    #                 except Exception as e:
    #                     print(f"AN Error occured: {e}")
    #                     time.sleep(0.1)
    #                     continue
    #
    #                 if data_present:
    #
    #                     self.gui_update_queue.put({"text_content": self.result, "text_response": self.response_string})
    #
    #                 if self.debug:
    #                     print("RETRIEVER:", "Moved Result to debug folder")
    #                     shutil.move(os.path.join(self.search_path, file),
    #                                 os.path.join(self.debug_folder, file))
    #                 else:
    #                     os.remove(os.path.join(self.search_path, file))
    #
    #             if file_name == "quit":
    #                 os.remove(os.path.join(self.search_path, file))
    #                 print("RETRIEVER:", "Stop Runner")
    #                 self.__run = False
    #                 break
    #     return None

    def get_translation(self):
        results = self.response_dict["results"]
        for result in results:
            alternatives = result["alternatives"]
            temp_string = alternatives[0]["transcript"]
            self.result += " " + temp_string
        if len(results) == 0:
            return False
        return True

    def complex_replacement(self):
        # preparing input for replacement
        self.result = self.result.replace("ß", "ss")
        if self.result[0] != " ":
            self.result = " " + self.result

        if self.result[-1] != " ":
            self.result += " "

        retdebg(f"Result: '{self.result}'")

        self.capitalisation()
        self.simple_replace()
        self.processed_result = ""

        # output preparation
        if self.result[0] == " ":
            self.result = self.result[1:]
        if self.result[-1] != " " and self.result[-1] != "\n":
            self.processed_result = self.result + " "
        else:
            self.processed_result = self.result
        self.processed_result.replace("  ", " ")

    def simple_replace(self):
        replacement_list = self.config_dict["simple_replacement_list"]
        for replacement, target, space_param in replacement_list:
            self.replace_escape(target=target, replacement=replacement, space_location=space_param)

    def replace_escape(self, target=None, replacement="", space_location=0):
        """
        ---
        :param target:
        :param replacement:
        :param space_location: [1 space only after symbol, 2 space only before symbol, 3 space before and after symbol]
        :return:
        """
        next_element = True
        retdebg(f"Replacing {target} with {replacement}")
        last_index = 0
        while next_element:
            self.work_result = self.result.lower()

            try:
                if last_index == 0:
                    replace_index = self.work_result.index(target)
                else:
                    replace_index = self.work_result.index(target, last_index + 1)
            except ValueError:
                next_element = False
                break

            if not self.work_result[replace_index - 1].isalpha() and \
                    not self.work_result[replace_index + len(target)].isalpha():
                escape = self.escaped(lower_border=last_index, upper_border=replace_index - 1)
                if escape is False:
                    retdebg("Escape is False")
                    if self.stop_counter > 0:

                        # Der absatz ist fertig. neue zeile

                        retdebg("Stops present")

                        # adding previous string with space at end.
                        temp = self.result[:self.stop_index]

                        # space only after target
                        if space_location == 1:
                            if self.stop_counter > 2:
                                # adding the stops with space.
                                temp += (self.config_dict["escape_word"] + " ") * (int(self.stop_counter / 2) - 1)

                            # adding last/only stop without space.
                            temp += self.config_dict["escape_word"]

                            # adding the replacement
                            temp += replacement
                            last_index = len(temp)

                            # adding the rest of the string.
                            temp += self.result[replace_index + len(target):]

                        # space only before target
                        elif space_location == 2:
                            # adding all stops with space
                            temp += (self.config_dict["escape_word"] + " ") * int(self.stop_counter / 2)

                            # adding replacement
                            temp += replacement
                            last_index = len(temp) - 1

                            # adding rest of string wihtout space
                            temp += self.result[replace_index + len(target) + 1:]

                        # space before and after
                        elif space_location == 3:
                            temp += (self.config_dict["escape_word"] + " ") * int(self.stop_counter / 2)

                            # adding replacement
                            temp += replacement
                            last_index = len(temp)

                            # adding rest of string with space
                            temp += self.result[replace_index + len(target):]

                        self.result = temp

                    elif self.stop_counter == 0:
                        retdebg("No Stops present")

                        # space only after target
                        if space_location == 1:
                            # adding previous string without space
                            temp = self.result[:replace_index - 1]

                            # adding replacement
                            temp += replacement
                            last_index = len(temp)

                            # adding the rest of the string with space.
                            temp += self.result[replace_index + len(target):]

                        # space only before target
                        elif space_location == 2:
                            # adding previous string with space
                            temp = self.result[:replace_index]

                            # adding replacement
                            temp += replacement
                            last_index = len(temp) - 1

                            # adding the rest of the string without space
                            temp += self.result[replace_index + len(target) + 1:]

                        # space before and after target
                        elif space_location == 3:
                            # adding previous string with space
                            temp = self.result[:replace_index]

                            # adding replacement
                            temp += replacement
                            last_index = len(temp)

                            # adding rest of string with space
                            temp += self.result[replace_index + len(target):]

                        print(f"RETRIEVER: not escaped, with no stops:\n{temp}")

                        self.result = temp

                else:
                    retdebg("Escape is True")
                    if self.stop_counter > 2:
                        retdebg("Stops present")
                        # adding previous string
                        temp = self.result[:self.stop_index]

                        # adding the stops
                        temp += (self.config_dict["escape_word"] + " ") * int((self.stop_counter - 1) / 2)
                        last_index = len(temp) + len(target) - 1

                        # adding the string from gross on
                        temp += self.result[replace_index:]

                        self.result = temp

                    else:
                        retdebg("only one stop present")
                        # adding previous string upto escape
                        temp = self.result[:self.stop_index]
                        last_index = len(temp) - 1 + len(target)

                        # adding everything from target word on
                        temp += self.result[replace_index:]

                        self.result = temp

            else:
                last_index = replace_index + len(target) - 1

    def capitalisation(self):
        retdebg("Capitaliation")
        next_element = True
        last_index = 0
        while next_element:
            time.sleep(1)

            self.stop_index = None
            self.stop_counter = 0
            self.work_result = self.result.lower()
            retdebg(f"Work_result: '{self.work_result}'")

            # finding next instance of the word for capitalisation
            try:
                if last_index == 0:
                    start_gross_index = self.work_result.index(self.config_dict["capital_writing"])
                else:
                    start_gross_index = self.work_result.index(self.config_dict["capital_writing"], last_index + 1)

            except ValueError:
                next_element = False
                break

            retdebg(f"Start gross index: {start_gross_index}")
            retdebg(
                f"area in question: '{self.work_result[start_gross_index-1:start_gross_index + len(self.config_dict['capital_writing']) + 1]}'")

            # checking that boundaries are indeed spaces
            if not self.work_result[start_gross_index - 1].isalpha() and \
                    not self.work_result[start_gross_index + len(self.config_dict["capital_writing"])].isalpha():

                escape = self.escaped(lower_border=last_index, upper_border=start_gross_index - 1)

                # checking symbol to be capitalised is letter
                _temp_index = start_gross_index + len(self.config_dict["capital_writing"]) + 1
                if self.work_result[_temp_index].isalpha():
                    if escape is False:

                        retdebg("Escape is False")
                        if self.stop_counter > 0:
                            retdebg("Stops present")
                            # adding previous string with space at end.
                            temp = self.result[:self.stop_index]

                            # adding the stops.
                            temp += (self.config_dict["escape_word"] + " ") * int(self.stop_counter / 2)

                            # adding making the word
                            temp += self.result[
                                start_gross_index + len(self.config_dict["capital_writing"]) + 1].upper()
                            last_index = len(temp) - 2

                            # adding the rest of the string.
                            temp += self.result[start_gross_index + len(self.config_dict["capital_writing"]) + 2:]

                            self.result = temp

                        elif self.stop_counter == 0:
                            retdebg("No Stops present")
                            temp = self.result[:start_gross_index]

                            # setting the letter to upper case and adding it to the string.
                            temp += self.result[
                                start_gross_index + len(self.config_dict["capital_writing"]) + 1].upper()
                            last_index = len(temp) - 2

                            # adding the rest of the string.
                            temp += self.result[start_gross_index + len(self.config_dict["capital_writing"]) + 2:]

                            print(f"RETRIEVER: not escaped, with no stops:\n{temp}")

                            self.result = temp

                    else:
                        retdebg("Escape is True")
                        if self.stop_counter > 2:
                            retdebg("Stops present")
                            # adding previous string
                            temp = self.result[:self.stop_index]

                            # adding the stops
                            temp += (self.config_dict["escape_word"] + " ") * int((self.stop_counter - 1) / 2)
                            last_index = len(temp) - 1 + len(self.config_dict["capital_writing"])

                            # adding the string from gross on
                            temp += self.result[start_gross_index:]

                            self.result = temp

                        else:
                            retdebg("No Stops present")
                            # adding previous string
                            temp = self.result[:self.stop_index]

                            last_index = len(temp) - 1 + len(self.config_dict["capital_writing"])

                            # adding
                            temp += self.result[start_gross_index:]

                            self.result = temp
                else:
                    last_index = start_gross_index + len(self.config_dict["capital_writing"]) - 1
            else:
                last_index = start_gross_index + len(self.config_dict["capital_writing"]) - 1

    def escaped(self, lower_border, upper_border):
        lower_end = upper_border - len(self.config_dict["escape_word"])
        if lower_end > lower_border:
            retdebg(f"RETRIEVER: escaping '{self.work_result[lower_end: upper_border]}'")

            # checking for escape word and for space before escape word.
            if self.work_result[lower_end:upper_border] == self.config_dict["escape_word"] and \
                    not self.work_result[lower_end - 1].isalpha():
                print("RETRIEVER: stop found")
                self.stop_counter += 1
                self.escaped(lower_border=lower_border, upper_border=lower_end - 1)
                # TODO: Rethink this -> It should be ok and work correctly if the else clause is not related to the
                    # inner if statement
            else:
                retdebg("Stop not found")
                self.stop_index = upper_border + 1
        else:
            retdebg("Lower Border reached.")
            self.stop_index = upper_border + 1
            return False

        print(f"Stop index {self.stop_index}")
        print(f"Stop counter {self.stop_counter}")
        if self.stop_counter == 0:
            self.stop_index = None
            return False
        elif self.stop_counter % 2 == 0:
            return False
        else:
            return True

    # CAPITALISATION TEST:
    # x stop stop stop gross alexander -> stop gross alexander
    # x stop stop gross alexander -> stop Alexander
    # x stop gross alexander -> gross Alexander
    # x gross alexander -> Alexander

    # stop stop stop gross alexander -> stop gross alexander
    # stop stop gross alexander -> stop Alexander
    # stop gross alexander -> gross Alexander
    # gross alexander -> Alexander

    # :stop
    # ;stop
    # .stop
























if __name__ == '__main__':
    multi_manager = multiprocessing.Manager()

    update_gui_config_queue = multi_manager.Queue()
    update_timer_queue = multi_manager.Queue()
    command_queue = multi_manager.Queue()
    print("MAIN:", "Queues present")

    # Timer Process
    count_down = Timer(update_gui_queue=update_gui_config_queue, query_queue=update_timer_queue)
    timer_handle = multiprocessing.Process(target=count_down.run_timer)
    timer_handle.start()
    print("MAIN:", "Timer Started")

    # Recognizer Process
    recognizer_class = Listener(cmd_queue=command_queue, update_gui_queue=update_gui_config_queue,
                                timer_query_queue=update_timer_queue, debug=True)
    quit_path_request_script = recognizer_class.get_wave_store_path()
    quit_path_retriever = recognizer_class.get_txt_store_path()

    # recognizer_handle = multiprocessing.Process(target=recognizer_class.run_listener)
    recognizer_handle = threading.Thread(target=recognizer_class.run_listener)
    recognizer_handle.start()
    print("MAIN:", "Recognizer Started")

    terminal_handle = multiprocessing.Process(target=run_bach_requst_script)
    terminal_handle.start()
    # terminal has its own print statement

    retriever_class = RetrieveText(gui_queue=update_gui_config_queue, search_path=quit_path_retriever, debug=False)
    # retriever_handle = multiprocessing.Process(target=retriever_class.run_simple_retriever)
    retriever_handle = multiprocessing.Process(target=retriever_class.run_retriever)
    retriever_handle.start()
    print("MAIN:", "Retriever started.")


    # GUI Thread
    print("MAIN:", "Starting GUI")
    gui_obj = GUI(update_config_queue=update_gui_config_queue, cmd_queue=command_queue, timer_queue=update_timer_queue)
    gui_obj.run_gui()

