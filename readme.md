1. Create a new repository.
2. upload (generate_playlists.py,readme.md,.gitignore,playlists folder) to your main branch.
3. Make any other desired changes to the Python script. (.channels.json,epg) url.
4. Ensure GitHub Actions are enabled. (Settings,Actions,General) select (Read and write permissions) and check (Allow GitHub Actions to create and approve pull requests) "save".
5. Scroll up select "Actions" then "Skip this and set up a workflow yourself". Rename your file from "main.yml" to "generate_playlists.yml" Copy&Paste the contents of "generate_playlists.yml" into the text box and "commit changes".

The script should auto run and you can manually run the script by going to "Actions" and run the "Generate M3U Playlists" workflow.
