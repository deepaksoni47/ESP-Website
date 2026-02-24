__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call
from esp.utils.web import render_to_response


class OnSiteAdminDashboard(ProgramModuleObj):
    doc = """Admin dashboard for onsite management."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite Admin Dashboard",
            "link_title": "Admin Dashboard",
            "module_type": "onsite",
            "seq": 15,
            "choosable": 1,
            }

    @main_call
    @needs_onsite
    def dashboard(self, request, tl, one, two, module, extra, prog):
        context = {
            'program': self.program,
            'one': one,
            'two': two,
        }
        return render_to_response(self.baseDir() + 'dashboard.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
