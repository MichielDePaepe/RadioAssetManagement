from django.views import View
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import CreateView
from django.views.generic.detail import DetailView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages


from .models import *
from radio.models import *
from .forms import *


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

class RadioContainerLinkListView(View):

    def get(self, request, *args, **kwargs):
        container_id = kwargs.get('container_id')
        container = get_object_or_404(Container, id=container_id)
        rcl_list = RadioContainerLink.objects.filter(container=container)

        if len(rcl_list) == 1:
            return HttpResponseRedirect(reverse('organization:rcl_detail', args=[rcl_list[0].id]))
        
        context = {
            "container": container,
            "object_list": rcl_list,
        }

        return render(request, 'organization/rcl_list.html', context)


class RadioContainerLinkDetailView(DetailView):
    model = RadioContainerLink
    template_name = 'organization/rcl_detail.html'
    context_object_name = 'link'


class RadioContainerLinkSubmitView(View):
    def post(self, request):
        tei = request.POST.get('tei')
        print(tei)
        link_id = int(request.POST.get('link_id'))
        link = RadioContainerLink.objects.get(id=link_id)
        remove = request.POST.get('remove') == 'true'

        if remove:
            link.radio = None
            link.save()
            messages.success(request, f"Radio verwijderd uit {link.container} - {link.name}.")
        else:
            radio = Radio.objects.get(TEI=int(tei))
            link.radio = radio
            link.save()
            messages.success(request, f"{radio} toegevoegd aan {link.container} - {link.name}.")

        return HttpResponseRedirect(reverse('organization:rcl_list', args=[link.container.id]))


class OverviewPostListView(ListView):
    model = Post
    template_name = 'organization/post_overview_list.html'
    context_object_name = 'posts'

class OverviewPostDetailView(DetailView):
    model = Post
    template_name = 'organization/post_overview_detail.html'
    context_object_name = 'post'
