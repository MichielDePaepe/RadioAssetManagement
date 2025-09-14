from django.views import View
from django.views.generic import ListView, DetailView, FormView, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from .models import *
from radio.models import *
