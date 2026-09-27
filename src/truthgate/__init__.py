"""Compatibility shim for the pre-0.4.0 name.

This project is now ``trvthnvke``. The shim exists because existing policy
files allow ``python -m truthgate`` in ``command_allow`` and existing hooks and
CI lanes invoke it by that name; removing the module would break them with an
import error rather than a deprecation. Everything is re-exported from the real
package, so there is one implementation, not two.
"""

from trvthnvke import *  # noqa: F401,F403
from trvthnvke import __version__  # noqa: F401
