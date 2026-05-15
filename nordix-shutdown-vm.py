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
nordix-shutdown-vm.py

Popup dialog shown when one or more VMs (libvirt/virsh) are detected
during Nordix graceful shutdown.

Shows the user which VMs are running and gives two options:
  - Continue shutdown anyway
  - Cancel shutdown (so user can manually shut down VMs first)

Exit codes:
  0 = continue shutdown
  1 = abort shutdown
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import subprocess
import sys


def get_running_vms():
    """Return list of running VM names."""
    try:
        out = subprocess.check_output(
            ["virsh", "list", "--state-running", "--name"],
            stderr=subprocess.DEVNULL, text=True
        )
        return [name.strip() for name in out.splitlines() if name.strip()]
    except Exception:
        return []


class VMDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nordix Graceful Shutdown")
        self.set_default_size(480, 280)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_deletable(False)

        self.result = 1  # default: abort

        vms = get_running_vms()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(24)
        vbox.set_margin_end(24)
        self.add(vbox)

        # Icon
        icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
        vbox.pack_start(icon, False, False, 0)

        # Header
        header = Gtk.Label()
        header.set_markup("<big><b>Virtual machines are running</b></big>")
        vbox.pack_start(header, False, False, 0)

        # VM list
        if vms:
            vm_text = "\n".join(f"  • {vm}" for vm in vms)
        else:
            vm_text = "  (couldn't list VM names)"

        info = Gtk.Label()
        info.set_markup(
            f"The following VMs are running:\n\n"
            f"<tt>{vm_text}</tt>\n\n"
            "Shut down your VMs before proceeding with shutdown.\n"
            "Or choose to continue anyway (VMs will not be shut down gracefully)."
        )
        info.set_line_wrap(True)
        info.set_justify(Gtk.Justification.LEFT)
        vbox.pack_start(info, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        vbox.pack_end(btn_box, False, False, 0)

        btn_continue = Gtk.Button(label="Continue shutdown anyway")
        btn_continue.connect("clicked", self.on_continue)
        btn_box.pack_start(btn_continue, False, False, 0)

        btn_cancel = Gtk.Button(label="Cancel shutdown")
        btn_cancel.get_style_context().add_class("destructive-action")
        btn_cancel.connect("clicked", self.on_cancel)
        btn_box.pack_start(btn_cancel, False, False, 0)

        self.show_all()

    def on_continue(self, _btn):
        self.result = 0
        Gtk.main_quit()

    def on_cancel(self, _btn):
        self.result = 1
        Gtk.main_quit()


if __name__ == "__main__":
    win = VMDialog()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
    sys.exit(win.result)
