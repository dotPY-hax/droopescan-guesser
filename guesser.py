from concurrent.futures import ThreadPoolExecutor
import json
import string
import sys
import hashlib

import requests

MAX_WORKERS = None


class Plugins:
    def __init__(self, droopescan_json):
        self.plugins = []
        for plugin in droopescan_json.get("plugins").get("finds"):
            name = plugin.get("name")
            target_files = [imu.get("url") for imu in plugin.get("imu") if imu.get("description") != "License file"]
            plugin = Plugin(name, target_files)
            self.plugins.append(plugin)

        self.init_plugins()
        self.get_all_files()
        self.calculate_all_hashes()
        self.guess_versions()

    def init_plugins(self):
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for plugin in self.plugins:
                futures.append(executor.submit(plugin.request_tags))
            for future in futures:
                future.result()

    def get_all_files(self):
        future_futures = []
        for plugin in self.plugins:
            for target_file in plugin.target_files:
                for plugin_version in plugin.plugin_versions:
                    future_futures.append((plugin_version.request_file, target_file))
                future_futures.append((plugin.target_version.request_file, target_file))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for future_future in future_futures:
                method, target_file = future_future
                futures.append(executor.submit(method, target_file))
            for future in futures:
                future.result()

    def calculate_all_hashes(self):
        for plugin in self.plugins:
            plugin.version_hashes()

    def guess_versions(self):
        future_futures = []
        for plugin in self.plugins:
            plugin.guess_versions()
            for plugin_version in plugin.guessed_versions:
                future_futures.append(plugin_version.request_insecure_tag)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for future_future in future_futures:
                futures.append(executor.submit(future_future))
            for future in futures:
                future.result()

    def pretty_plugins(self):
        indent = "  "
        print("Plugins guessed:")
        for plugin in self.plugins:
            print(f"{indent}{plugin.name}")
            for version in plugin.guessed_versions:
                insecure = " - insecure" if version.is_insecure else ""
                print(f"{indent}{indent}{version.tag}{insecure}")


class Plugin:
    def __init__(self, name, target_files):
        self.name = name
        self.target_files = target_files
        self.tags = None
        self.target_version = None
        self.plugin_versions = []
        self.guessed_versions = []

    def request_tags(self):
        data = requests.get(f"https://git.drupalcode.org/api/v4/projects/project%2F{self.name}/repository/tags").json()
        for datum in data:
            tag = datum.get("name")
            self.plugin_versions.append(PluginVersion(self.name, tag))
        self.target_version = TargetVersion(self.name, None)

    def version_hashes(self):
        self.target_version.calculate_version_hash(self.target_files)
        for plugin_version in self.plugin_versions:
            plugin_version.calculate_version_hash(self.target_files)

    def guess_versions(self):
        guessed = []
        for version in self.plugin_versions:
            if version.version_hash == self.target_version.version_hash != 'd41d8cd98f00b204e9800998ecf8427e':
                guessed.append(version)
        self.guessed_versions = guessed

    def __str__(self):
        return self.name


class PluginVersion:
    def __init__(self, name, tag):
        self.name = name
        self.tag = tag
        self.files = {}
        self.version_hash = None
        self.is_insecure = False

    def request_file(self, target_file_url):
        file_name = target_file_url.split("/")[-1]
        url = f"https://git.drupalcode.org/api/v4/projects/project%2F{self.name}/repository/files/{file_name}/raw"
        self.files[target_file_url] = requests.get(url, params={"ref": self.tag}).text.strip()

    def calculate_version_hash(self, file_order):
        file_content = ""
        for file in file_order:
            try:
                file_content += self.files[file]
            except KeyError:
                pass
        content = "".join([char for char in file_content if char in string.printable])
        self.version_hash = hashlib.md5(content.encode()).hexdigest()

    def request_insecure_tag(self):
        indicator = '<strong class="insecure">Insecure</strong>'
        url = f"https://www.drupal.org/project/{self.name}/releases/{self.tag}"
        result = requests.get(url).text
        self.is_insecure = indicator in result

    def __str__(self):
        return self.tag


class TargetVersion(PluginVersion):
    def request_file(self, target_file_url):
        self.files[target_file_url] = requests.get(target_file_url).text.strip()

    def __str__(self):
        return self.version_hash


def guess_version_from_droopescan_stdout():
    droopescan_input = sys.stdin.read()
    try:
        droopescan_input = json.loads(droopescan_input)
        plugins = Plugins(droopescan_input)
        plugins.pretty_plugins()
    except json.JSONDecodeError:
        print("MALFORMED INPUT!")

if __name__ == "__main__":
    print("Droopescan plugin guesser by dotpy")
    print("Assume the latest version installed but check all!! The guesses depend on how well the project is maintained\n")

    guess_version_from_droopescan_stdout()
