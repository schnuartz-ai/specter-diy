# Sandman Specter-DIY ESP32-P4 Web Flasher

This static site is assembled by `tools/publish-flasher.sh` for the Waveshare
ESP32-P4-WIFI6-Touch-LCD-4.3-C (480×800). It pairs the latest Sandman
`esp32p4-*` release with a separate ESP32-P4 v3.x community build. After the
chip connects, the page reads its revision and chooses the matching firmware.

## Supported firmware profiles

- ESP32-P4 v0.x/v1.x: the upstream Sandman release.
- ESP32-P4 v3.0–v3.99: a community build based on the same Sandman release,
  compiled with the ESP-IDF rev3 silicon profile.
- Other chip revisions and other boards are blocked. In particular, Kern's
  `wave_4b_v3` is a different board.

The v3.x build has not been tested on the recipient's physical board. A
successful compile and image validation do not prove that its screen and all
board functions work at runtime.

## Flashing effects and verification

Both firmware bundles write `storage-reset.bin` at `0x410000`. This erases the
device's internal storage and deletes data saved there. The page requires a
separate acknowledgement before enabling Flash. The custom firmware is
experimental and unaudited; do not use real seeds or funds.

Before writing firmware, the page checks every listed binary against its
SHA-256 manifest and validates the firmware header's supported chip revision.
The hash only detects corruption; it is not a signed firmware identity.

Use a desktop Chromium browser over HTTPS and connect the board's USB TO UART
port. The serial picker filters for the Waveshare board's WCH USB-UART bridge.
