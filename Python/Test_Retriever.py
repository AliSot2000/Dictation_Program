import os
import shutil
import json


def multiprocessing_print(instance, instring):
    if hasattr(instance, "print_class_name"):
        class_name = str(instance.print_class_name)
    else:
        class_name = str(instance.__class__.__name__)
    print(f"{class_name}: {instring}")

def retdebg(instring):
    print(f"RETRIEVER: {instring}")



class RetrieveText:
    def __init__(self, text=""):
        # TODO: last index in capitalisation or simple replace need to be not -1 at the end.
        # self.gui_update_queue = gui_queue
        # self.search_path = os.path.abspath(search_path)
        # self.print_class_name = "RETRIEVER"

        multiprocessing_print(self, "Test of Multiprocessing_print")

        self.use_defaults = True
        self.config_path = None

        # self.debug = True
        # self.debug_folder = os.path.join(self.search_path, "_debug")

        self.caps_lock = False
        # self.response_dict = None
        # self.response_string = ""

        self.result = text
        self.work_result = ""
        self.processed_result = ""
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
                [":", "doppelpunkt", 1],
                [";", "semikolon", 1],
                [";", "strichpunkt", 1]
            ],
            "caps_lock_word": "caps-lock",
            "capital_writing": "gross"
        }

        self.config_dict = self.default_config_dict

        # if self.use_defaults is not True:
        #     parent_dir = os.path.abspath(os.path.join(__file__, os.pardir))
        #     self.config_path = os.path.join(parent_dir, "Retrieve_Text_config.json")

        #     self.config_dict = json.load(self.config_path)

        # Adding Debug folder
        # if self.debug:
        #     if os.path.exists(self.debug_folder):
        #         print("RETRIEVER:", "Old debug path exists, removing path")
        #         shutil.rmtree(self.debug_folder)
        #     os.mkdir(self.debug_folder)

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

            if self.work_result[replace_index - 1] == " " and \
                    self.work_result[replace_index + len(target)] == " ":
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
                            temp = self.result[replace_index]

                            # adding replacement
                            temp += replacement
                            last_index = len(temp)

                            # adding rest of string with space
                            temp += self.result[replace_index + len(target)]

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


    def run_retriever(self):
        self.__run = True
        while self.__run:
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
                        self.complex_replacement()


                        self.gui_update_queue.put({"text_content": self.processed_result,
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

    def run_simple_retriever(self):
        self.__run = True
        while self.__run:
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
                        print(f"AN Error occured: {e}")
                        time.sleep(0.1)
                        continue

                    if data_present:
                        self.gui_update_queue.put({"text_content": self.result, "text_response": self.response_string})

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

    def complex_replacement(self):
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

    def get_translation(self):
        results = self.response_dict["results"]
        for result in results:
            alternatives = result["alternatives"]
            temp_string = alternatives[0]["transcript"]
            self.result += " " + temp_string
        if len(results) == 0:
            return False
        return True

    def capitalisation(self):
        retdebg("Capitaliation")
        next_element = True
        last_index = 0
        while next_element:
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
            retdebg(f"area in question: '{self.work_result[start_gross_index-1:start_gross_index + len(self.config_dict['capital_writing']) + 1]}'")

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
                            temp += self.result[start_gross_index + len(self.config_dict["capital_writing"]) + 1].upper()
                            last_index = len(temp) - 2

                            # adding the rest of the string.
                            temp += self.result[start_gross_index + len(self.config_dict["capital_writing"]) + 2:]

                            self.result = temp

                        elif self.stop_counter == 0:
                            retdebg("No Stops present")
                            temp = self.result[:start_gross_index]

                            # setting the letter to upper case and adding it to the string.
                            temp += self.result[start_gross_index + len(self.config_dict["capital_writing"]) + 1].upper()
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

    def output_preparation(self):
        # add functionality for other
        self.result.replace("ß", "ss")
        if self.result[0] == " ":
            self.result = self.result[1:]
        if self.result[-1] != " " and self.result[-1] != "\n":
            self.processed_result = self.result + " "
        else:
            self.processed_result = self.result
        self.processed_result.replace("  ", " ")

    def work(self):
        # self.result = ""
        self.processed_result = ""
        self.complex_replacement()
        self.output_preparation()
        retdebg(f"Processed result: '{self.processed_result}'")



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


example_sentences = [
    "Das ist ein gross test.",  # Das ist ein Test.
    "Das ist ein stop gross test.",  # Das ist ein gross Test.
    "Das ist ein stop stop gross test.",  # Das ist ein stop Test.
    "Das ist ein stop stop stop gross test.",  # Das ist ein stop gross Test
    "gross satzanfänge werden stop gross geschrieben.",  # Satzanfänge werden gross geschrieben.
    "stop gross satzanfänge werden stop gross geschreiben.",  # gross satzanfänge werden gross geschrieben.
    "stop stop gross satzanfänge werden stop gross geschreiben.",  # stop Satzanfänge werden gross geschrieben.
    "stop stop stop gross satzanfänge werden stop gross geschrieben."  # stop gross satzanfänge werden gross geschrieben.
]

example_sentences_neue_zeile = [
    "Das ist ein Test Satz. neue zeile Hier geht es weiter.",  # Das ist ein Test Satz. \nHier geht es weiter.for
    "Das ist ein Test Satz. stop neue zeile Hier geht es weiter.",  # Das ist ein Test Satz. neue Zeile Hier geht es weiter
    "Das ist ein Test Satz. stop stop neue zeile Hier geht es weiter.",  # Das ist ein Test Satz. stop \nHier geht es weiter.
    "Das ist ein Test Satz. stop stop stop neue zeile Hier geht es weiter."  # Das ist ein Test Satz. stop neue zeile Hier geht es weiter.
]

example_sentences_zeilenumbruch = [
    "Ein Absatz hört hier auf. zeilenumbruch Und hier beginnt ein neuer Absatz.",
    "Ein Absatz hört hier auf.stop zeilenumbruch Und hier beginnt ein neuer Absatz.",
    "Ein Absatz hört hier auf.stop stop zeilenumbruch Und hier beginnt ein neuer Absatz.",
    "Ein Absatz hört hier auf.stop stop stop zeilenumbruch Und hier beginnt ein neuer Absatz."
]

# [["\n", "neue zeile", 2],
# ["\n" "zeilenumbruch", 2],
# [":", "doppelpunkt", 1],
# [";", "semikolon", 1],
# [";", "strichpunkt", ]]

# instance = RetrieveText(text=example_sentences[7])
instance = RetrieveText(text="neue Zeile Bindestrich rezidivierend sorry Cortez Vorhofflimmern mit spontaner und medikamentöse Konversion in einen Bodyguard in Sinusrhythmus mit konversions Pausen von 7 bis 8 Sekunden neue Zeile Bindestrich relevantes roszik Bindestrich gross Sinus Syndrom bei Frau die Karten Phasen und Pausen Leerzeile gross C gross ha2 gross B gross 2-3 V gross a gross S")
instance.work()


