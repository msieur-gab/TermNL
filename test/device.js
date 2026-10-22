// A pretend device for tests: the lists a real board would read from itself.
export const device = {
  list(kind) {
    return {
      folder: [
        { value: "$HOME", names: ["home", "home folder", "my home"] },
        { value: "$HOME/Documents", names: ["Documents", "documents", "docs"] },
        { value: "$HOME/Downloads", names: ["Downloads", "downloads"] },
        { value: "$HOME/ideas", names: ["ideas"] },
        { value: "$HOME/projects", names: ["projects"] },
      ],
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
};
