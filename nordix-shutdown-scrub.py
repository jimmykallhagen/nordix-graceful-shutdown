#!/usr/bin/env python3
##============================================================================##
# SPDX-License-Identifier: GPL-3.0-or-later                                  #
# Nordix license - https://www.gnu.org/licenses/gpl-3.0.html                 #
# Copyright (c) 2025- The Nordix Authors                                     #
# Part of Nordix - https://github.com/jimmykallhagen/Nordix                  #
#                                                                            #
# This program is free software: you can redistribute it and/or modify       #
# it under the terms of the GNU General Public License as published by       #
# the Free Software Foundation, either version 3 of the License, or          #
# (at your option) any later version. See <https://www.gnu.org/licenses/>.   #
##============================================================================##

"""
nordix-shutdown-scrub.py

Popup dialog shown when ZFS scrub, resilver or trim is in progress
during Nordix graceful shutdown.

Reads env var NORDIX_ZFS_OP to know which operation is active.

Exit codes:
  0 = continue shutdown (user chose "wait" or "pause")
  1 = abort shutdown (user chose "cancel")

If user picks "wait", this script blocks until the operation finishes,
then exits 0 so shutdown continues.

If user picks "pause", the operation is paused and exit 0.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os
import subprocess
import sys

OPERATION = os.environ.get("NORDIX_ZFS_OP", "scrub")

class ScrubTrimDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nordix Shutdown")
        self.set_default_size(500, 250)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_deletable(False)

        self.result = 1  # default: abort

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)
        self.add(vbox)

        # Icon + header
        icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
        vbox.pack_start(icon, False, False, 0)

        label = Gtk.Label()
        label.set_markup(
            f"<big><b>ZFS {OPERATION} in progress</b></big>\n\n"
            f"A ZFS <b>{OPERATION}</b> is currently running.\n"
             "Please choose how to proceed:"
        )
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        vbox.pack_start(label, False, False, 0)

        # Status label (shown when waiting)
        self.status_label = Gtk.Label(label="")
        vbox.pack_start(self.status_label, False, False, 0)

        # Spinner (hidden by default)
        self.spinner = Gtk.Spinner()
        vbox.pack_start(self.spinner, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        vbox.pack_end(btn_box, False, False, 0)

        btn_wait = Gtk.Button(label=f"Wait until {OPERATION} is complete")
        btn_wait.get_style_context().add_class("suggested-action")
        btn_wait.connect("clicked", self.on_wait)
        btn_box.pack_start(btn_wait, False, False, 0)

        btn_pause = Gtk.Button(label=f"Pause {OPERATION}")
        btn_pause.connect("clicked", self.on_pause)
        btn_box.pack_start(btn_pause, False, False, 0)

        btn_cancel = Gtk.Button(label="Cancel shutdown")
        btn_cancel.get_style_context().add_class("destructive-action")
        btn_cancel.connect("clicked", self.on_cancel)
        btn_box.pack_start(btn_cancel, False, False, 0)

        self.btn_box = btn_box
        self.show_all()
        self.spinner.hide()

    def on_wait(self, _btn):
        """Wait for the operation to complete, then continue shutdown."""
        self.status_label.set_markup(
           f"<i>Waiting for {OPERATION} to complete...</i>\n"
            "<small>Shutdown will continue automatically.</small>"
        )
        self.spinner.show()
        self.spinner.start()
        self.btn_box.set_sensitive(False)

        # Poll every 5 seconds
        GLib.timeout_add_seconds(5, self._check_done)

    def _check_done(self):
        """Returns True to keep polling, False to stop."""
        try:
            out = subprocess.check_output(
                ["zpool", "status"], stderr=subprocess.DEVNULL, text=True
            )
            still_running = False
            for line in out.splitlines():
                stripped = line.strip()
                if stripped.startswith("scan:") and "in progress" in stripped:
                    still_running = True
                elif stripped.startswith("trim:") and "in progress" in stripped:
                    still_running = True

            if not still_running:
                self.result = 0
                Gtk.main_quit()
                return False
        except Exception:
            pass

        return True  # keep polling

    def on_pause(self, _btn):
        """Pause the operation and continue shutdown."""
        try:
            if OPERATION == "scrub":
                subprocess.run(["zpool", "scrub", "-p", "-a"],
                               stderr=subprocess.DEVNULL)
            elif OPERATION == "trim":
                subprocess.run(["zpool", "trim", "-s", "-a"],
                               stderr=subprocess.DEVNULL)
            # resilver can't really be paused, but we continue anyway
        except Exception as e:
            print(f"Warning: could not pause {OPERATION}: {e}", file=sys.stderr)

        self.status_label.set_markup(
            f"<i>{OPERATION.capitalize()} Paused.</i>\n"
            "<small><b>NOTE:</b> You must manually restart this at the next boot.</small>"

        )
        self.result = 0
        GLib.timeout_add(1500, Gtk.main_quit)

    def on_cancel(self, _btn):
        """Abort shutdown entirely."""
        self.result = 1
        Gtk.main_quit()


if __name__ == "__main__":
    win = ScrubTrimDialog()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
    sys.exit(win.result)
