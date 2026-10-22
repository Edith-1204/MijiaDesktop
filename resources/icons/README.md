# Mijia icon

`mijia-official-512.png` is the current Mijia application icon downloaded from
the official Xiaomi App Store listing for package `com.xiaomi.smarthome`:

https://m.app.mi.com/details?id=com.xiaomi.smarthome

`mijia.ico` contains resized copies of that image for Windows application,
taskbar, notification-area, and executable-file icon sizes. The Mijia name and
logo are trademarks of Xiaomi. These brand assets are not covered by the
project's GPL-3.0-or-later license.

`mijia-macos.svg` is the macOS vector variant, with an inset rounded green tile
and transparent outer corners. `mijia-menubar.svg` is a separate 22-point white
glyph with no background and reduced padding for improved menu-bar legibility.
Qt marks it as a template mask so macOS can adapt it to the menu-bar appearance.

`mijia-macos.png` and `mijia.icns` are rendered from the macOS vector source with
`python scripts/build_icons.py`. The ICNS includes sizes through 1024 pixels for
Retina displays. The Windows icon and original reference image remain unchanged.
