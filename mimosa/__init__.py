""" Mimosa: an all-in-one crawler / monitor / push framework """
import sys

from mimosa import utils
from mimosa.utils import log, template

# plugins written before the package layout import "utils.template" (and "utils.log"); keep them working
sys.modules.setdefault("utils", utils)
sys.modules.setdefault("utils.log", log)
sys.modules.setdefault("utils.template", template)
