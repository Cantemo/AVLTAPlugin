# Developement

There are many ways of doing this, here's one way of doing it if you run the portal project with the docker setup. This assumes you are at the root of the portal project:

1. Check out this project into the portal project in `src/portal/plugins/untracked`
   ```sh
   cd src/portal/plugins
   mkdir untracked
   cd untracked
   git clone git@gitlab.com:codmill/cantemo/cantemo-av-lta-plugin.git
   ```
2. Create a symlink to add the plugin
   ```sh
   cd src/portal/plugins
   ln -s untracked/cantemo-av-lta-plugin/av_lta .
   ```
3. Restart portal-web
   ```
   ./compose/bin/portal-web-restart.sh
   ```

4. Activate the plugin by opening the /admin page in Cantemo. The plugin be listed there as "Accurate Video LTA Plugin". Activate it.

## Run tests

The `--keepdb` flag is optional, but it speeds up running the tests as the test database does not need to be re-created each time.

```
./compose/bin/test.sh portal.plugins.av_lta --keepdb
```

## Authentication

Session authentication is used by proxying the AV applications on a plugin sub path. This way the AV apps can use the session and CSRF cookies when making requests back to Cantemo.

## TODO

### Plugin
- [ ] Setup permissions
- [x] Publish endpoint for subtitle
- [x] Thumbnails
- [ ] Waveforms via Vidispine
- [x] Markers
- [x] Support more context menus
  - [x] Item page
  - [x] Media bin
- [ ] Settings

### Frontend
- [ ] Subtitle without video
- [ ] Thumbnails from STILL_FRAME support in Subtitle

### Questions
- [ ] Analyze work step? double add / remove when combined with avcore plugin
