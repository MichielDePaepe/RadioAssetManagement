from django.shortcuts import render

from django.views import View
from django.views.generic import TemplateView, ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect

from django.db.models import Count, Q, Min
from radio.models import *
from organization.models import *
from inventory.models import *

from datetime import timedelta
import json
import re


class PostListView(ListView):
    model = Post
    template_name = 'inventory/post_list.html'
    context_object_name = 'posts'


from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Min, Max, BooleanField, Case, When, Exists, OuterRef

class ContainerListView(ListView):
    model = Container
    template_name = 'inventory/container_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container_id = self.kwargs.get('container_id')
        container = Container.objects.get(id=container_id)

        children = container.children.annotate(
            radios_with_assignment=Count(
                'radio_links',
                filter=Q(radio_links__radio__isnull=False),
                distinct=True
            ),
            last_scan=Max(
                'radio_links__radio__inventory_entries__timestamp',
                filter=Q(radio_links__radio__isnull=False)
            )
        )

        # Check for each child if any radio link's last scan is older than its scan_interval
        for c in children:
            # Check if any radio link scan is too old
            has_old = False
            for link in c.radio_links.filter(radio__isnull=False):
                # Get last scan timestamp
                last = link.radio.inventory_entries.aggregate(last=Max('timestamp'))['last']
                # Mark as old if no last scan or last scan older than scan_interval
                if last is None or last < timezone.now() - link.scan_interval:
                    has_old = True
                    # Stop at first old link
                    break
            c.has_old_scan = has_old

            # Get last inventory timestamp for the container (max)
            last_inventory_ts = container.inventoryentry_set.aggregate(max_ts=Max('timestamp'))['max_ts']

            # Detect radios with last scan at this timestamp but linked to a different container
            latest_wrong_scan_exists = c.radio_links.filter(
                radio__inventory_entries__timestamp=last_inventory_ts
            ).exclude(
                container=c
            ).exists()
            c.has_wrong_radio = latest_wrong_scan_exists

            # Set status based on checks
            if c.has_wrong_radio:
                c.status = 'danger'
            elif c.has_old_scan:
                c.status = 'warning'
            else:
                c.status = 'success'

        context["container"] = container
        context["children"] = children
        return context



class ContainerInventoryView(View):
    def get(self, request, container_id):
        context = dict()

        container = Container.objects.get(id=container_id)
        context["container"] = container

        return render(request, "inventory/container_inventory.html", context)


class ScanSubmitView(View):
    def post(self, request):
        context = dict()

        assignments_json = request.POST.get('assignments')
        assignments = json.loads(assignments_json)

        container_id = int(request.POST.get('container'))
        container = Container.objects.get(id=container_id)

        for a in assignments:
            rcl = RadioContainerLink.objects.get(id=int(a["link_id"]))
            container = rcl.container
            radio = Radio.objects.get(TEI=a["tei"])

            InventoryEntry(radio=radio, container=container).save()

        return HttpResponseRedirect(reverse('inventory:container_list', args=[container.parent.id]))



