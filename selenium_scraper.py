# Browser and HTML parser
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver import Firefox
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.common import exceptions
from bs4 import BeautifulSoup
from lxml import html
import re
import urllib.request

# Logging and Error
import logging
import logging.handlers
import errno

# OS
import os
from os import listdir
from os.path import isfile, join
import sys
import subprocess

# Data processing
import pandas as pd
import json
import hashlib

#TODO: Documentation, verbose

class Scraper:
    def __init__(self, browser="Firefox", headless=True, log_filename="scraper.log"):
        # profile = webdriver.FirefoxProfile()
        self._name = browser
        self._headless = headless
        self.set_browser()
        self.logging_path = os.getcwd()
        self.set_logging_params(filename=log_filename)
        # self.download_path = os.path.normpath(os.path.expanduser("~/Downloads"))

    def use_chrome(self):
        self._browser = Chrome
        self._options = ChromeOptions()
        self._name = "Chrome"
    
    def use_firefox(self):
        self._browser = Firefox
        self._options = FirefoxOptions()
        # self._options = self.set_firefox_options()
        self._name = "Firefox"

    def set_browser(self):
        if self._name.lower() == "chrome":
            self.use_chrome()
        elif self._name.lower() == "firefox":
            self.use_firefox()
        else:
            self.logging.warning(f"'{self._name}' not recognized defaulted to Firefox")
            self.use_firefox()
    
    # def set_firefox_options(self):
    #     options = FirefoxOptions()
    #     options.set_preference("browser.download.folderList", 2)
    #     options.set_preference("browser.download.dir", os.path.normpath(os.path.expanduser("~/Downloads")))
    #     options.set_preference("browser.download.useDownloadDir", True)
    #     options.set_preference("browser.download.viewableInternally.enabledTypes", "")
    #     options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip;text/plain;application/text;text/xml;application/xml")
    #     options.set_preference("pdfjs.disabled", True)
    #     return options
    
    def open_browser(self):
        print("Opening Browser")
        return self._browser()

    @property
    def headless(self, headless):
        return self._headless
    
    #TODO: work on headless setter
    @headless.setter
    def headless(self, headless):
        self.logging.info("Setting headless mode")
        assert type(headless) == bool
        self._options.headless = headless
        self._options.add_argument('--remote-debugging-port=9222') # Enable debugging on local host while running selenium headless --> http://localhost:9222

    def set_logging_params(self, path=None, filename="selenium_scraper.log", root_level="DEBUG", console_level="INFO", file_level="WARNING"):
        """This method set logging parameters
        
        Args:
            path (str, optional): The path to the folder where you want the log file to be written. Defaults to the root path of the class object.
            filename (str, optional): The name of the log file (including the extension). Defaults to "selenium_scraper.log".
            root_level (str, optional): The root level. Defaults to "DEBUG".
            console_level (str, optional): The console level. Defaults to "INFO".
            file_level (str, optional): The file level. Defaults to "WARNING".
        """
        
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        root_level = root_level.upper()
        console_level = console_level.upper()
        file_level = file_level.upper()
        if not path:
            path = self.logging_path
        for level_name, level in {"root level":root_level, "console level":console_level, "file level":file_level}.items():
            if level not in levels:
                logging.error(f"logging setting {level} unavailable for {level_name}")
                logging.info(f"Only the following levels are available: {' '.join(levels)}")
                return
        if path:
            pass
        if filename:
            pass

        # Silence numexpr
        logging.getLogger('numexpr').setLevel(logging.CRITICAL)

        # Create logger and use it only once each times
        rootLogger = logging.getLogger()
        rootLogger.propagate = False

        rootLogger.setLevel(getattr(logging, root_level))
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-4.4s]  %(message)s")

        fileHandler = logging.FileHandler(os.path.join(path, filename))
        fileHandler.setLevel(getattr(logging, file_level))
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(getattr(logging, console_level))
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)
        self.logging = logging

    def make_sure_path_exists(self, path):
        """This method create a path and the corresponding folders if the path doesn't exists yet
        
        Args:
            path (str): The path you want to make sure exists
        """
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
    
    def run_bash(self, command):
        """This method runs simple bash command from a string (doesn't allow substring, ex: echo 'this is an example' >> test.txt WONT WORK) 
        
        Args:
            command (str): The string corresponding to the command you want to run
        """
        if type(command) == str:
            command = command.split()
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE)
                output = process.communicate()[0]
            except:
                logging.error(f"Unable to run bash command {command}")

    def html_tables_to_df(self):
        # This method format html tables in pandas DataFrame format
        html = self.browser.page_source
        soup = BeautifulSoup(html,'html.parser')
        tables = soup.select("table")
        dfs = []
        for table in tables:
            dfs.append(pd.read_html(str(table))[0])
        return dfs

    def javascript_variable_to_json(self, js_var, path, indent=4, python_readable=False):
        self.make_sure_path_exists("".join(path.split("/")[:-1]))
        json_file = self.browser.execute_script(f'return JSON.stringify({js_var});')
        if python_readable:
            json_file = eval(json_file.replace("false", "False").replace("true", "True").replace("null", "None"))
        with open(path, 'w') as outfile:
            json.dump(json_file, outfile, sort_keys=True, indent=indent)

    def script_data_from_id_to_json(self, script_id, path):
        script_data = self.browser.find_element_by_id(f"{script_id}").get_attribute("innerHTML")
        script_data = self.browser.execute_script(f'return JSON.stringify({script_data});')
        script_data = eval(script_data.replace("false", "False").replace("true", "True").replace("null", "None"))
        with open(path, 'w') as outfile:
            json.dump(script_data, outfile, sort_keys=True, indent=4)

    # def get_proxies(self):
    #     url = 'https://free-proxy-list.net/'
    #     response = requests.get(url)
    #     parser = fromstring(response.text)
    #     proxies = set()
    #     for i in parser.xpath('//tbody/tr')[:20]:
    #         if i.xpath('.//td[7][contains(text(),"yes")]'):
    #             #Grabbing IP and corresponding PORT
    #             proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
    #             proxies.add(proxy)
    #     return proxies

    def download(self, url, save_to_path="download_folder"):
        if save_to_path == "download_folder":
            save_to_path = os.path.normpath(os.path.expanduser("~/Downloads")) + "download.tmp"
        try:
            urllib.request.urlretrieve(url, save_to_path)
            self.logging.info(f"Downloaded file from url:{url} to {save_to_path}")
            return True
        except:
            self.logging.error(f"The file from url:{url} was not available")
            return False

    def save_json(self, data, json_file_name):
        """This method save data given in paramater as a json file
        
        Args:
            data ([str, lst, dict and other types of data]): The data you want to save as json file
            json_file_name (str): The json filename (including path)
        """
        self.make_sure_path_exists(self.path_today)
        json_file_name = os.path.join(self.path_today, f"{json_file_name}.json")
        with open(json_file_name, 'w') as outfile:
            json.dump(data, outfile)

    def load_json(self, file_path):
        """This method load a json file and returns it
        
        Args:
            file_path (str): The path to the json file you want to load
        
        Returns:
            [any type]: The loaded json file
        """
        if not os.path.isfile(file_path) and not file_path.endswith(".json"):
            file_path += ".json"
        if not os.path.isfile(file_path):
            logging.error(f"The path provided doesn't lead to a json file\nPath provided:{file_path}")
            return False
        try:
            with open(file_path) as json_file:
                return json.load(json_file)
        except:
            logging.error(f"Unable to load json file, make sure {file_path} is the right path")

    def load_csv(self, file_path):
        """This method load a csv file and returns it as a pandas DataFrame
        
        Args:
            file_path (str): The path to the csv file you want to load as a pandas DataFrame
        
        Returns:
            pandas DataFrame: The csv file as a pandas DataFrame
        """
        if not os.path.isfile(file_path) and not file_path.endswith(".csv"):
            file_path += ".csv"
        if not os.path.isfile(file_path):
            logging.error(f"The path provided doesn't lead to a csv file\nPath provided:{file_path}")
            return
        try:
            df = pd.read_csv(file_path)
            return df
        except:
            logging.error(f"There was a problem loading csv file: {file_path}")

    def save_csv(self, df, file_path, params={"index" : None}):
        """This method saves a pandas DataFrame in a csv file
        
        Args:
            df (pandas DataFrame): The pandas DataFrame you want to save
            file_path (str): The path of the csv file you want to create (including filename and extension)
            params (dict, optional): The pandas "df.to_csv" paramaters. Defaults to {"index" : None}.
        """
        if not isinstance(df, pd.DataFrame):
            logging.error(df, "\nThe file printed above need to be a DataFrame in order to be used by the method save_csv()")
            return
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        parent = os.path.abspath(os.path.join(file_path, os.pardir))
        self.make_sure_path_exists(parent)
        if params:
            df.to_csv(file_path, **params)
        else:
            df.to_csv(file_path)

    def set_driver_options(self, options): #TODO: fix
        """This method allow you to set options to the selenium browser
        
        Args:
            options (lst): The options you want to set for the web driver
        """
        if type(options) == list:
            for option in options:
                self._browser.options.add_argument(option)
        else:
            self._browser.options.add_argument(option)

    def md5(self, filename):
        hash_md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()