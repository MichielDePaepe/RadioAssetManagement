# import set_rlc

from organization.models import *
import re

for container in Container.objects.filter(name__startswith = "Kast"):
    match = re.match("Kast (?P<nr>\d+)", container.name)
    nr = int(match.group("nr"))
    if 23 <= nr and 26 >= nr:
        rcl = container.radio_links.all()
        if not rcl:
            RadioContainerLink(
                container = container,
                name = "Reserve AMU %i" % (nr-22, )
            ).save()
        print(rcl)
#        rcl.name = "Instruction %i" % nr
#        rcl.save()a
