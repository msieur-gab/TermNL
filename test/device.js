// A pretend device for tests and the playground: the lists a real board would read from itself,
// and a small file tree with the same name in several places.
const FOLDERS = [
  { value: "$HOME", names: ["home", "home folder", "my home"] },
  { value: "$HOME/Documents", names: ["Documents", "documents", "docs"] },
  { value: "$HOME/Downloads", names: ["Downloads", "downloads"] },
  { value: "$HOME/ideas", names: ["ideas"] },
  { value: "$HOME/projects", names: ["projects"] },
];
const FILES = {
  "$HOME": ["note.md", "todo.txt"],
  "$HOME/Documents": ["note.md", "report.pdf", "groceries.md"],
  "$HOME/Downloads": ["movie.mkv", "setup.sh"],
  "$HOME/ideas": ["seed.md", "note.md"],
  "$HOME/projects": ["website.html", "scraper.py"],
};

export const device = {
  list(kind) {
    return {
      folder: FOLDERS,
      service: [
        { value: "ssh", names: ["ssh", "sshd"] },
        { value: "nginx", names: ["nginx", "web server", "webserver"] },
        { value: "mpd", names: ["music server", "mpd", "music"] },
      ],
      network: [{ value: "home-5g", names: ["home-5g", "home"] }],
      app: [
        { value: "x-terminal-emulator", names: ["terminal", "console", "shell"] },
        { value: "firefox", names: ["firefox", "browser", "web browser"] },
      ],
    }[kind] || [];
  },
  // the files in one folder (on a board: ls)
  files(folder) { return FILES[folder] || []; },
  // every file in the home folder whose name passes the test (on a board: find, hidden folders skipped)
  find(test) {
    return Object.entries(FILES).flatMap(([folder, files]) => files.filter(test)
      .map(file => ({ folder, file, label: FOLDERS.find(d => d.value === folder).names[0] })));
  },
};
