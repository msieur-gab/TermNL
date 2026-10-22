"""A pretend device for tests: the lists a real board would read from itself, and a small file tree
with the same name in several places (the same as test/device.js)."""
FOLDERS = [
    {"value": "$HOME", "names": ["home", "home folder", "my home"]},
    {"value": "$HOME/Documents", "names": ["Documents", "documents", "docs"]},
    {"value": "$HOME/Downloads", "names": ["Downloads", "downloads"]},
    {"value": "$HOME/ideas", "names": ["ideas"]},
    {"value": "$HOME/projects", "names": ["projects"]},
]
FILES = {
    "$HOME": ["note.md", "todo.txt"],
    "$HOME/Documents": ["note.md", "report.pdf", "groceries.md"],
    "$HOME/Downloads": ["movie.mkv", "setup.sh"],
    "$HOME/ideas": ["seed.md", "note.md"],
    "$HOME/projects": ["website.html", "scraper.py"],
}
LISTS = {
    "folder": FOLDERS,
    "service": [
        {"value": "ssh", "names": ["ssh", "sshd"]},
        {"value": "nginx", "names": ["nginx", "web server", "webserver"]},
        {"value": "mpd", "names": ["music server", "mpd", "music"]},
    ],
    "network": [{"value": "home-5g", "names": ["home-5g", "home"]}],
    "app": [
        {"value": "x-terminal-emulator", "names": ["terminal", "console", "shell"]},
        {"value": "firefox", "names": ["firefox", "browser", "web browser"]},
    ],
}


class PretendDevice:
    def list(self, kind):
        return LISTS.get(kind, [])

    def files(self, folder):
        return FILES.get(folder, [])

    def find(self, test):
        return [{"folder": folder, "file": f, "label": next(d for d in FOLDERS if d["value"] == folder)["names"][0]}
                for folder, files in FILES.items() for f in files if test(f)]


device = PretendDevice()
