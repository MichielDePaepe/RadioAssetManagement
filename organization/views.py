from django.views.generic import ListView
from django.views.generic.detail import DetailView

from inventory.models import RadioPosition

from .models import *


class ContainerListView(ListView):
    model = Container
    template_name = 'organization/container_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container_id = self.kwargs.get('container_id')
        if container_id:
            container = Container.objects.get(id=container_id)
            context["container"] = container
            context["children"] = container.children.all()
        else:
            context["container"] = None
            context["children"] = Container.objects.filter(parent__isnull=True)

        return context

class OverviewPostListView(ListView):
    model = Post
    template_name = 'organization/post_overview_list.html'
    context_object_name = 'posts'

class OverviewPostDetailView(DetailView):
    model = Post
    template_name = 'organization/post_overview_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for child in self.object.children.all():
            positions = RadioPosition.objects.none()
            if child.vector_id:
                positions = RadioPosition.objects.filter(vector_id=child.vector_id)
            if not positions.exists():
                positions = RadioPosition.objects.filter(location__name=child.name)
            child.radio_positions_for_overview = (
                positions
                .prefetch_related("assignments__radio__subscription__issi", "assignments__radio__model")
                .order_by("order", "name")
            )
        return context
