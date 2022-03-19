import google.cloud.speech as gcs
from google.oauth2 import service_account

import datetime
import time

import sys
import os
import io

import shutil
import json


class GoogleCloudSTTAPI:
    def __init__(self):
        # Folders need to be filled

        script_path = os.path.realpath(__file__)
        parent_dir = os.path.abspath(os.path.join(script_path, os.pardir))

        self.log_file = os.path.join(parent_dir, "log_Request_Script.txt")
        self.input_folder = os.path.join(parent_dir, "_temp_wav")
        self.output_folder = os.path.join(parent_dir, "_temp_txt")

        self.debug_folder = os.path.join(self.input_folder, "_debug")
        if os.path.exists(self.debug_folder):
            shutil.rmtree(self.debug_folder)
            os.mkdir(self.debug_folder)
        else:
            os.mkdir(self.debug_folder)
        print("GSR:", f"Log file: {self.log_file}")
        print("GSR:", f"Input Folder: {self.input_folder}")
        print("GSR:", f"Output Folder: {self.output_folder}")

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
        # self.request_timeout = 60
        self.request_timeout = 15
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

        # self.auth_path = "C:/Users/AliSot2000/Documents/Google_Cloud/tribal-sunbeam-286522-d7283289ed2b.json"
        self.auth_path_mac = "/Users/sotoudeh/Documents/google_cloud_var/tribal-sunbeam-286522-d7283289ed2b.json"

        # self.auth_obj = service_account.Credentials.from_service_account_file(self.auth_path)
        # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.auth_path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.auth_path_mac

        # self.google_recognizer = gcs.SpeechClient(credentials=self.auth_obj)
        self.google_recognizer = gcs.SpeechClient()

        self.debug = True

    def main_loop(self, debug=None):
        if debug is not None:
            self.debug = debug
        while self.run:
			
            time.sleep(1)
            # query folders: folders containing queries as a wav file, a txt file and a json file.
            query_folders = os.listdir(self.input_folder)
            if len(query_folders) > 0:
                for folder in query_folders:
                    query_folder_path = os.path.join(self.input_folder, folder)

                    # checking for folders and the folder not being a debug folder
                    if os.path.isdir(query_folder_path) and "_" not in os.path.basename(query_folder_path):
                        self.query_index = os.path.basename(query_folder_path)
                        files = os.listdir(query_folder_path)

                        # Script works only without wav_config file.
                        if len(files) == 2:
                            for file in files:
                                if os.path.splitext(file)[1] == ".wav":
                                    with io.open(os.path.join(query_folder_path, file), "rb") as wav_file:
                                        data = wav_file.read()
                                        self.audio_binary_data = gcs.RecognitionAudio(content=data)
                                        self.start_request = True
                            if self.overwrite_request_config:
                                self.current_config = self.default_config
                            else:
                                print("GSR:", "not implemented yet")

                            if self.start_request:
                                with open(self.log_file, "w") as log_file:
                                    log_file.write("Request was sent to google...")
                                print("GSR:", "Request was sent to google...")
                                try:
                                    self.response = self.google_recognizer.recognize(config=self.current_config,
                                                                                     audio=self.audio_binary_data,
                                                                                     timeout=self.request_timeout)
                                    self.write_response(response_path=os.path.join(self.output_folder,
                                                                                   str(self.query_index + ".json")))
                                    print("GSR:", self.response)
                                except Exception as e:
                                    with open(self.log_file, "w") as log:
                                        print("GSR:", f"An Exception occurred:\n:{e}")
                                        log.write(f"An Exception occurred:\n{e}")

                                self.start_request = False

                            if not self.debug:
                                shutil.rmtree(query_folder_path)
                                with open(self.log_file, "w") as log_file:
                                    log_file.write("removed File")
                                    print("GSR:", "removed File")
                            else:
                                with open(self.log_file, "w") as log_file:
                                    log_file.write(f"new path: {os.path.join(self.debug_folder, folder)}")
                                    print("GSR:", f"new path: {str(query_folder_path + '_debug')}")
                                shutil.move(query_folder_path, os.path.join(self.debug_folder, folder))

                    elif os.path.isfile(query_folder_path):
                        if os.path.basename(query_folder_path) == "quit.txt":
                            self.run = False
                            os.remove(query_folder_path)
                            with open(self.log_file, "w") as log_file:
                                log_file.write("Quit")
                                print("GSR:", "quit")
                        elif os.path.basename(query_folder_path) == "config.txt":
                            os.remove(query_folder_path)
                            print("GSR:", "updating config...")

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
                result_dict["channelTag"] = result.channel_tag
            except AttributeError:
                with open(self.log_file, "w") as log_file:
                    log_file.write("No channelTag present...")
                print("GSR:", f"No channelTag present...")
            except Exception as e:
                with open(self.log_file, "w") as file:
                    file.write(f"An Exception Occurred: \n{e}")
                # print("GSR:", e)
            self.response_dict["results"].append(result_dict)

        print("GSR:", self.response_dict)

    def write_response(self, response_path):
        if self.response is not None:
            self.response_to_string()
            if len(self.response_dict["results"]) > 0:
                with open(response_path, "w") as file:
                    json.dump(self.response_dict, file, indent=4)


GSR = GoogleCloudSTTAPI()
GSR.main_loop()


def poc(print_string, boolean):
    if boolean:
        print(print_string)


def loc(print_string, boolean, path):
    if boolean:
        with open(path, "w") as file:
            file.write(print_string)


def log_print_on_condition(write_string, path, log_bool, print_bool=None):
    if print_bool is None:
        print_bool = log_bool
    poc(print_string=write_string, boolean=print_bool)
    loc(print_string=log_bool, path=path, boolean=log_bool)
